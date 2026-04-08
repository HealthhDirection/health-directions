# 건강길찾기 (Health Directions) — 할 일 목록

## Phase 1: 데이터 기반 (1~2주차)

### 환경 설정
- [x] 프로젝트 스캐폴딩 (backend/app 디렉토리 구조 생성)
- [x] .env 파일 작성 (.env.example 참고, API 키 등록)
- [x] Docker Compose로 Redis 컨테이너 실행 확인
- [x] PostgreSQL `gangseo_transit` DB 생성 (port 5433)

### DB 초기화
- [x] DB 스키마 3개 초기화 (`backend/app/db/init.py`)
  - master (정적 참조 데이터)
  - realtime (자주 갱신)
  - history (ML 학습용)
- [x] PG / Redis 연결 설정 (`backend/app/db/connection.py`)

### API 검증
- [x] 버스 API 실제 호출 검증 + 응답 구조 확인 → `bus사용법.md` 작성 완료
- [x] 따릉이 API 실제 호출 검증 + 응답 구조 확인 → `bike사용법.md` 작성 완료
- [x] 신호등 API 실제 호출 검증 + 응답 구조 확인 → `signal사용법.md` 작성 완료
- [x] `korean_api.py` 공통 래퍼 구현 (XML 인코딩 자동 감지, 에러코드 매핑)

### 마스터 데이터 적재
- [x] `scripts/seed_master_data.py` 작성
- [ ] 마스터 데이터 적재 실행 (강서구: lat 37.53–37.58, lng 126.80–126.88)
  - bus_stops, bus_routes
  - bike_stations
  - intersections

### 수집기
- [x] `BaseCollector` 구현 (재시도, 로깅, 속도제한) — `collectors/base.py`
- [x] `bus_collector.py` 구현 (버스 도착 2분 주기 + 실시간 위치 수집)
- [x] `bike_collector.py` 구현 (따릉이 가용 3분 주기, pbdo_v2 API)
- [x] `signal_collector.py` 구현 (신호등 상태 3분 주기)
- [x] APScheduler 오케스트레이션 (`collectors/scheduler.py`)
- [ ] Redis 캐시 저장/조회 실제 실행 확인

---

## Phase 2: 추천 엔진 (3~4주차)

### 유틸리티
- [x] `geo.py` 구현 (Haversine, 바운딩박스, 최근접 정류장)

### 경로 엔진
- [x] TMAP 대중교통/도보 API 연동 (`route_finder.py`)
- [x] TMAP 100m 그리드 캐시 구현
- [x] `route_finder.py`: 후보 경로 생성
  - 버스만
  - 버스 + 자전거
  - 도보 + 자전거 (3km 미만)
- [x] `time_estimator.py`: TMAP 베이스 + 신호등 지연 보정
  - 도보 구간 교차로 식별 (50m 이내)
  - 보행 신호 잔여시간으로 지연 계산
  - 데이터 없으면 cycle_time/2 통계 평균 사용
- [x] `route_scorer.py`: 다기준 점수화
  - 속도 0.4 / 안정성 0.25 / 자전거확률 0.2 / 편의성 0.15

### FastAPI 엔드포인트
- [x] `GET /api/routes` — 경로 추천 (`api/routes.py`)
- [x] `GET /api/stations/bike` — 따릉이 대여소 (`api/stations.py`)
- [x] `GET /api/stations/bus` — 버스 정류장 (`api/stations.py`)
- [x] `GET /api/status` — 데이터 신선도 (`api/status.py`)
- [x] API 통합 테스트 작성 (`tests/test_api/`)

---

## Phase 3: AI 레이어 (5주차)

- [x] 규칙 기반 자전거 가용성 예측 구현 (`bike_predictor.py` 1단계)
  - 현재 수량 + 시간대별 소모율 → 도착 시점 수량 추정
  - 3대 이상 → 95%, 1대 이상 → 70%, 0대 → 최소 10%
- [x] realtime → `history.bike_hourly` 시간별 집계 배치 잡 구현
- [ ] ML 학습 파이프라인 준비 (LightGBM)
  - 피처: hour, day_of_week, current_bikes, 15분 추세, rack_count, minutes_ahead
- [ ] history 데이터 2~4주 축적 후 ML 모델 학습 및 `bike_predictor.py` 2단계 교체

---

## Phase 4: 프론트엔드 (6~7주차)

### 기반 설정
- [x] Kakao Maps JS SDK 통합 (`components/Map/KakaoMap.jsx`)
- [x] axios 인스턴스 설정 (`src/utils/api.js`)
- [x] zustand 상태 관리 설정 (`src/store/routeStore.js`)

### 컴포넌트
- [x] `SearchBar` + `PlaceSuggestion` (`components/Search/SearchBar.jsx`)
- [x] `RouteList` + `RouteCard` + `BikeAvailability` (`components/Route/`)
- [x] `RouteOverlay` (지도 위 폴리라인 스타일 유틸)
- [x] `StationMarker` (버스/따릉이 마커 변환 유틸)

### 페이지
- [x] `HomePage` 구성 (`pages/HomePage.jsx`)
- [x] `RoutePage` 구성 (`pages/RoutePage.jsx`)
- [x] 반응형 레이아웃 (모바일 우선, `src/index.css`)

---

## Phase 5: 통합 & 마무리 (8주차)

- [x] E2E 테스트 작성 및 실행
- [x] 에러 처리 & 로딩 상태 전반 점검
- [ ] 성능 최적화
  - DB 쿼리 인덱스 검토
  - Redis 캐시 TTL 튜닝
  - TMAP 그리드 캐시 적중률 확인
- [x] UI에 "추정"/"신호반영" 구분 표시 (RouteCard 신호반영 뱃지 + RoutePage 안내문)
- [x] UI에 따릉이 "N분 전 기준" 표시 (BikeAvailability ahead prop)
- [ ] 공모전 제출 전 최종 검토
