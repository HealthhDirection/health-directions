# 건강길찾기 개발 스택

## Backend

- Python + FastAPI
- PostgreSQL (port 5433, db: `gangseo_transit`)
- Redis
- APScheduler

## Frontend

- React 18 + Vite
- Zustand
- Axios

## AI / 데이터

- scikit-learn
- LightGBM

## External APIs

- 공공데이터포털 (버스 도착/위치, 따릉이 가용, 신호등 상태)
- TMAP 대중교통/도보 API
- Kakao Maps JS SDK

## 어떤 명령을 하던 .claude 폴더의 에이전트, 스킬, 커맨드 파일들을 읽고 그 도구들을 사용해.

## 가장 중요한건 공용데이터를 사용하는거야

### 버스 데이터 API

- 엔드포인트: https://apis.data.go.kr/B551982/rte
- 3가지 방식:
  1. `/mst_info` - 노선 기본 정보
  2. `/ps_info` - 노선 경유지 정보
  3. `/rtm_loc_info` - 버스 실시간 위치 정보
- 📄 상세: `bus사용법.md`

### 신호등 데이터 API

- 엔드포인트: https://apis.data.go.kr/B551982/rti
- 2가지 방식:
  1. `/crsrd_map_info` - 교차로 위치 정보
  2. `/tl_drct_info` - 교차로별 8방향 신호 잔여시간
- 단위: **데시초(1/10초)** → 초로 변환 필요 (`/ 10`)
- 📄 상세: `signal사용법.md`

### 공영자전거(따릉이) 데이터 API

- 엔드포인트: https://apis.data.go.kr/B551982/pbdo_v2
- 3가지 방식:
  1. `/inf_101_00010001_v2` - 대여소 기본 정보 (위치, 주소, 운영시간)
  2. `/inf_101_00010002_v2` - 현재 대여가능 자전거 수 (실시간)
  3. `/inf_101_00010003_v2` - 대여/반납 통계 (일일)
- 지자체 코드: 서울시 `1100000000` (강서구는 좌표 필터링)
- 📄 상세: `bike사용법.md`

### 실시간 신호등

## 로컬 개발 서버 실행

### Python 경로

```
C:\Users\chanbongg\AppData\Local\Programs\Python\Python311\python.exe
```

### 백엔드 서버 실행 (매번 이 순서로)

```powershell
cd C:\코딩\health-directions\backend

# 가상환경 활성화
.\.venv\Scripts\Activate.ps1

# 서버 실행
uvicorn app.main:app --reload --port 8000
```

- Swagger UI: http://localhost:8000/docs
- 헬스체크: http://localhost:8000/health

### 가상환경 최초 세팅 (처음 한 번만)

```powershell
cd C:\코딩\health-directions\backend
C:\Users\chanbongg\AppData\Local\Programs\Python\Python311\python.exe -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 신호등 데이터베이스 구조 및 사용법

### 외부 API (공공데이터포털 RTI)

베이스 URL: `https://apis.data.go.kr/B551982/rti`

| 엔드포인트          | 설명                                     | 주요 파라미터                                       |
| ------------------- | ---------------------------------------- | --------------------------------------------------- |
| `/crsrd_map_info` | 교차로 위치 정보 (교차로 ID, 이름, 위도) | `stdgCd=1100000000` (서울시, 구 단위 코드 미지원) |
| `/tl_drct_info`   | 교차로별 8방향 신호 잔여시간 실시간      | `stdgCd=1100000000`                               |

**주의**: `stdgCd`는 시(市) 단위 코드만 지원. 강서구 코드(`1150000000`)는 빈 결과 반환.
**주의**: `mapCtptIntLot`(경도) 필드가 현재 API에서 빈 값으로 반환됨 → TMAP geocoding으로 보완.

### DB 테이블

#### `master.intersections` — 교차로 마스터

```sql
SELECT intersection_id, intersection_name, latitude, longitude
FROM master.intersections
WHERE longitude IS NOT NULL;  -- 경도가 있는 교차로만 (경로 매칭에 사용)
```

#### `realtime.signal_state` — 수집된 신호 상태

```sql
-- 특정 교차로 최신 신호
SELECT direction, current_phase, remaining_sec, collected_at
FROM realtime.signal_state
WHERE intersection_id = '101'
ORDER BY collected_at DESC
LIMIT 8;
```

### Redis 캐시 구조

- 키: `signal:{intersection_id}` (예: `signal:101`)
- 값: RTI `/tl_drct_info` raw item JSON
- TTL: 200초
- 사용처: `TimeEstimator.get_signal_delay()` — 경로의 신호 대기시간 계산

### 신호 상태명 매핑

| API 값                          | 의미              |
| ------------------------------- | ----------------- |
| `protected-Movement-Allowed`  | GREEN (진행 가능) |
| `permissive-Movement-Allowed` | GREEN             |
| `stop-And-Remain`             | RED (정지)        |
| `protected-clearance`         | YELLOW            |
| `permissive-clearance`        | YELLOW            |

### 잔여시간 단위

API 반환값은 **데시초(1/10초)** 단위. 초로 변환: `int(value) / 10`

### 마스터 데이터 적재 순서

```powershell
cd C:\코딩\health-directions

# 1. DB 스키마 초기화 (최초 1회)
python backend/app/db/init.py

# 2. 마스터 데이터 적재 (버스 정류장 + 따릉이 대여소 + 교차로)
python scripts/seed_master_data.py
```

`seed_master_data.py` 실행 시 `SIGNAL_API_KEY`와 `TMAP_APP_KEY`가 설정되어 있어야
교차로 데이터와 경도가 올바르게 적재됨.

# todo.md확인하기

# plan.md 확인하기

# %사용법.md 확인하기
