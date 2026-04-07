# 건강길찾기 (Health Directions) MVP

## Context
공모전 출품용 도시 이동 의사결정 서비스. 버스·공영자전거(따릉이)·교통 신호등 실시간 공공데이터를 통합하여, 사용자의 실제 이동시간과 자전거 이용 가능성을 예측하고 최적 경로를 추천한다. MVP 범위는 **강서구**로 한정.

데이터는 공공데이터포털 OpenAPI 3종(버스, 따릉이, 신호등)으로 이미 확보 완료.

---

## Tech Stack

| 레이어 | 기술 | 근거 |
|--------|------|------|
| Backend | Python + FastAPI | 데이터 처리/ML에 강점 |
| Frontend | React 18 + Vite | 기존 Mind_Scan 패턴 재사용 |
| DB | PostgreSQL (기존 5433 포트) | 새 DB `gangseo_transit` 생성 |
| Cache | Redis | 실시간 상태 캐시, TTL 기반 만료 |
| 지도 | Kakao Maps JS SDK | 한국 지도 커버리지 최고, 주소 검색 내장 |
| 경로 베이스 | TMAP 대중교통/도보 API | 직접 라우팅 엔진 구축 불필요 |
| 수집 스케줄러 | APScheduler | 장기 실행 프로세스에 적합 |

---

## 프로젝트 구조

```
health-directions/
├── .env                          # API 키, DB DSN, Redis URL
├── docker-compose.yml            # Redis 컨테이너
├── backend/
│   ├── requirements.txt
│   ├── alembic/                  # DB 마이그레이션
│   ├── app/
│   │   ├── main.py               # FastAPI 진입점
│   │   ├── config.py             # pydantic BaseSettings
│   │   ├── db/
│   │   │   ├── init.py           # 스키마 생성
│   │   │   └── connection.py     # PG/Redis 연결
│   │   ├── collectors/
│   │   │   ├── base.py           # BaseCollector (재시도, 로깅, 속도제한)
│   │   │   ├── bus_collector.py
│   │   │   ├── bike_collector.py
│   │   │   ├── signal_collector.py
│   │   │   └── scheduler.py      # APScheduler 오케스트레이션
│   │   ├── engine/
│   │   │   ├── route_finder.py   # 경로 후보 생성
│   │   │   ├── time_estimator.py # 신호등 보정 포함 시간 추정
│   │   │   ├── bike_predictor.py # 자전거 가용성 예측 (핵심 AI)
│   │   │   └── route_scorer.py   # 다기준 점수화
│   │   ├── api/
│   │   │   ├── routes.py         # GET /api/routes
│   │   │   ├── stations.py       # GET /api/stations/bike, bus
│   │   │   └── status.py         # 데이터 신선도
│   │   └── utils/
│   │       ├── geo.py            # Haversine, 바운딩박스
│   │       └── korean_api.py     # data.go.kr 공통 래퍼
│   └── tests/
│       ├── conftest.py
│       ├── test_collectors/
│       ├── test_engine/
│       └── test_api/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Map/              # KakaoMap, RouteOverlay, StationMarker
│   │   │   ├── Search/           # SearchBar, PlaceSuggestion
│   │   │   └── Route/            # RouteCard, RouteList, BikeAvailability
│   │   ├── pages/                # HomePage, RoutePage
│   │   ├── store/                # zustand
│   │   └── utils/                # axios 인스턴스
└── scripts/
    ├── seed_master_data.py       # 마스터 데이터 1회 적재
    └── run_collector.py          # 수집기 실행
```

---

## DB 스키마

### master (정적 참조 데이터)

```sql
CREATE SCHEMA IF NOT EXISTS master;

-- 버스 정류장
CREATE TABLE master.bus_stops (
    stop_id       TEXT PRIMARY KEY,
    stop_name     TEXT NOT NULL,
    latitude      DOUBLE PRECISION NOT NULL,
    longitude     DOUBLE PRECISION NOT NULL,
    district      TEXT DEFAULT '강서구',
    route_ids     TEXT[],
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_bus_stops_geo ON master.bus_stops (latitude, longitude);

-- 버스 노선
CREATE TABLE master.bus_routes (
    route_id      TEXT PRIMARY KEY,
    route_name    TEXT NOT NULL,
    route_type    TEXT,
    stop_sequence JSONB,
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- 따릉이 대여소
CREATE TABLE master.bike_stations (
    station_id    TEXT PRIMARY KEY,
    station_name  TEXT NOT NULL,
    latitude      DOUBLE PRECISION NOT NULL,
    longitude     DOUBLE PRECISION NOT NULL,
    rack_count    INT,
    district      TEXT DEFAULT '강서구',
    created_at    TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_bike_stations_geo ON master.bike_stations (latitude, longitude);

-- 교통 신호 교차로
CREATE TABLE master.intersections (
    intersection_id TEXT PRIMARY KEY,
    intersection_name TEXT,
    latitude      DOUBLE PRECISION NOT NULL,
    longitude     DOUBLE PRECISION NOT NULL,
    direction_count INT,
    signal_meta   JSONB,
    created_at    TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_intersections_geo ON master.intersections (latitude, longitude);
```

### realtime (자주 갱신)

```sql
CREATE SCHEMA IF NOT EXISTS realtime;

-- 버스 도착 예측
CREATE TABLE realtime.bus_arrivals (
    id            BIGSERIAL PRIMARY KEY,
    stop_id       TEXT NOT NULL,
    route_id      TEXT NOT NULL,
    arrival_sec_1 INT,
    arrival_sec_2 INT,
    bus_id_1      TEXT,
    bus_id_2      TEXT,
    congestion_1  INT,
    collected_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_bus_arr_stop ON realtime.bus_arrivals (stop_id, collected_at DESC);

-- 버스 실시간 위치
CREATE TABLE realtime.bus_positions (
    id            BIGSERIAL PRIMARY KEY,
    route_id      TEXT NOT NULL,
    bus_id        TEXT NOT NULL,
    latitude      DOUBLE PRECISION,
    longitude     DOUBLE PRECISION,
    stop_id       TEXT,
    congestion    INT,
    collected_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_bus_pos_route ON realtime.bus_positions (route_id, collected_at DESC);

-- 따릉이 실시간 가용
CREATE TABLE realtime.bike_availability (
    id            BIGSERIAL PRIMARY KEY,
    station_id    TEXT NOT NULL,
    available_bikes INT NOT NULL,
    available_racks INT NOT NULL,
    collected_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_bike_avail ON realtime.bike_availability (station_id, collected_at DESC);

-- 신호등 현재 상태
CREATE TABLE realtime.signal_state (
    id            BIGSERIAL PRIMARY KEY,
    intersection_id TEXT NOT NULL,
    direction     TEXT NOT NULL,
    current_phase TEXT NOT NULL,
    remaining_sec INT,
    cycle_sec     INT,
    collected_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_signal_state ON realtime.signal_state (intersection_id, collected_at DESC);
```

### history (ML 학습용)

```sql
CREATE SCHEMA IF NOT EXISTS history;

-- 시간별 자전거 집계 (90일 보관)
CREATE TABLE history.bike_hourly (
    station_id    TEXT NOT NULL,
    hour_ts       TIMESTAMPTZ NOT NULL,
    avg_bikes     DOUBLE PRECISION,
    min_bikes     INT,
    max_bikes     INT,
    sample_count  INT,
    PRIMARY KEY (station_id, hour_ts)
);

-- 경로 추천 로그 (30일 보관)
CREATE TABLE history.route_requests (
    id            BIGSERIAL PRIMARY KEY,
    origin_lat    DOUBLE PRECISION,
    origin_lng    DOUBLE PRECISION,
    dest_lat      DOUBLE PRECISION,
    dest_lng      DOUBLE PRECISION,
    recommended_routes JSONB,
    selected_route_idx INT,
    request_at    TIMESTAMPTZ DEFAULT now()
);

-- 수집기 상태 로그
CREATE TABLE history.collector_log (
    id            BIGSERIAL PRIMARY KEY,
    collector     TEXT NOT NULL,
    status        TEXT NOT NULL,
    records_count INT,
    error_msg     TEXT,
    duration_ms   INT,
    collected_at  TIMESTAMPTZ DEFAULT now()
);
```

---

## API 호출 예산 (일 5,000건 기준)

| API | 주기 | 활성시간 | 일간 호출 | 한도 대비 |
|-----|------|----------|-----------|-----------|
| 버스 도착 | 2분 | 06-22시 | ~2,400 | 48% |
| 버스 위치 | 5분 | 06-22시 | ~384 | 8% |
| **버스 합계** | | | **~2,884** | **58%** |
| 따릉이 가용 | 3분 | 06-23시 | ~1,020 | **20%** |
| 신호등 상태 | 3분 (10개) | 06-22시 | ~2,800 | **56%** |

TMAP 경로 API: 무료 1,000건/일 → 100m 그리드 캐시로 충분.

---

## 핵심 알고리즘: 경로 추천

### 흐름
```
사용자 입력 (출발, 도착)
  → 1. 후보 생성: 버스만 / 버스+자전거 / 도보+자전거(3km 미만)
  → 2. 시간 추정: TMAP 베이스 + 신호등 지연 보정
  → 3. 자전거 가용성 예측: "도착 시점에 자전거 있을 확률"
  → 4. 점수화: 속도(0.4) + 안정성(0.25) + 자전거확률(0.2) + 편의성(0.15)
  → 5. 상위 2~3개 반환
```

### 신호등 보정
- 도보 구간의 경로 상 교차로 식별 (50m 이내)
- 보행 신호 잔여시간으로 지연 계산
- 데이터 없으면 cycle_time/2 통계 평균 사용

### 자전거 가용성 예측

**1단계 (규칙 기반, MVP):**
- 현재 수량 + 시간대별 소모율로 도착 시점 수량 추정
- 3대 이상 → 95%, 1대 이상 → 70%, 0대 → 비율 기반 최소 10%

**2단계 (ML, 데이터 2~4주 축적 후):**
- LightGBM/GBR
- 피처: hour, day_of_week, current_bikes, 15분 추세, rack_count, minutes_ahead
- history.bike_hourly로 야간 배치 학습, 주간 재훈련

---

## 개발 페이즈

### Phase 1: 데이터 기반 (1~2주차)
- [ ] 프로젝트 스캐폴딩, DB/Redis 설정
- [ ] 3개 API 실제 호출 검증 + 응답 구조 확인
- [ ] master 데이터 적재 (강서구: lat 37.53-37.58, lng 126.80-126.88)
- [ ] 3개 수집기 구현 + APScheduler 연동
- [ ] Redis 캐시 확인

### Phase 2: 추천 엔진 (3~4주차)
- [ ] geo 유틸리티 (Haversine, 바운딩박스, 최근접)
- [ ] route_finder: TMAP 연동 + 버스+자전거 조합
- [ ] time_estimator: 신호등 보정 포함
- [ ] route_scorer: 다기준 점수화
- [ ] FastAPI 엔드포인트

### Phase 3: AI 레이어 (5주차)
- [ ] 규칙 기반 자전거 예측 통합
- [ ] 시간별 집계 잡 (realtime → history)
- [ ] ML 학습 스크립트 준비

### Phase 4: 프론트엔드 (6~7주차)
- [ ] Kakao Maps 통합
- [ ] 출발/도착 검색 (자동완성)
- [ ] RouteList + RouteCard + BikeAvailability
- [ ] 지도에 경로 폴리라인 + 마커
- [ ] 반응형 (모바일 우선)

### Phase 5: 통합 & 마무리 (8주차)
- [ ] E2E 테스트
- [ ] 에러 처리, 로딩 상태
- [ ] 성능 최적화

---

## 리스크 및 완화

| 리스크 | 완화 |
|--------|------|
| 신호등 API 커버리지 부족 | 데이터 없는 교차로는 통계 평균 사용, UI에 "추정"/"신호반영" 구분 |
| TMAP 무료 1,000건/일 | 100m 그리드 캐시로 중복 제거 |
| 따릉이 데이터 3분 지연 | 예측 모델이 보정, UI에 "N분 전 기준" 표시 |
| data.go.kr XML 인코딩 이슈 | korean_api.py에서 자동 감지 + 에러코드 매핑 |
