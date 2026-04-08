# 공영자전거(따릉이) 데이터 API 사용 가이드

## 개요

공공데이터포털의 공영자전거 API(pbdo_v2)를 활용하여 서울시 자전거 대여소의 위치, 현황, 대여/반납 통계를 수집합니다.

---

## API 기본 정보

**베이스 URL**: `https://apis.data.go.kr/B551982/pbdo_v2`

**인증**: `serviceKey` 파라미터에 공공데이터포털 인증키 필수

**지자체 코드**: 
- 서울시: `1100000000` (전체 대여소 조회 후 좌표 필터링)
- 강서구: `1150000000` (구 단위 코드)

**응답 형식**: JSON

**주요 특징**:
- 서울시 전체 약 2,700~3,200개 대여소
- 실시간 대여 가능 현황
- 일일 대여/반납 통계

---

## 3가지 주요 엔드포인트

### 1️⃣ 대여소 기본 정보 (`/inf_101_00010001_v2`)

자전거 대여소의 위치, 주소, 운영시간, 시설 정보를 제공합니다.

**엔드포인트**: `GET /inf_101_00010001_v2`

**요청 파라미터**

| 파라미터 | 타입 | 설명 | 예시 |
|---------|------|------|------|
| `serviceKey` | string | 공공데이터포털 인증키 | - |
| `lcgvmnInstCd` | string | 지자체코드 (서울시) | `1100000000` |
| `pageNo` | integer | 페이지 번호 (기본값: 1) | `1` |
| `numOfRows` | integer | 한 페이지 결과 수 (기본값: 10) | `1000` |
| `type` | string | 응답 파일 타입 | `JSON` |

**응답 항목**

| 필드 | 타입 | 설명 |
|-----|------|------|
| `rntstnId` | string | 대여소 ID (PK) |
| `rntstnNm` | string | 대여소명 (예: "108. 서교동 사거리") |
| `lat` | decimal | 대여소 위도 |
| `lot` | decimal | 대여소 경도 |
| `roadNmAddr` | string | 도로명 주소 |
| `lotnoAddr` | string | 지번 주소 |
| `operBgngHrCn` | string | 운영 시작시간 (HHMMSS, 예: "000000") |
| `operEndHrCn` | string | 운영 종료시간 (HHMMSS, 예: "235959") |
| `rntstnFcltTypeNm` | string | 시설 유형 ("무인", "유인" 등) |
| `rntstnOperDayoffDayCn` | string | 운영 휴무 정보 ("연중무휴" 등) |
| `rntFeeTypeNm` | string | 요금 유형 ("유료", "무료" 등) |
| `mngInstNm` | string | 관리 기관명 |
| `bcyclDataCrtrYmd` | string | 데이터 생성일 (YYYYMMDD) |

**사용 예시**

```python
import requests

params = {
    'serviceKey': 'YOUR_API_KEY',
    'lcgvmnInstCd': '1100000000',  # 서울시
    'pageNo': 1,
    'numOfRows': 1000,
    'type': 'JSON'
}

response = requests.get(
    'https://apis.data.go.kr/B551982/pbdo_v2/inf_101_00010001_v2',
    params=params
)
data = response.json()

for item in data['body']['item']:
    print(f"대여소: {item['rntstnNm']}, 위도: {item['lat']}, 경도: {item['lot']}")
```

**비고**
- 한 페이지에 최대 1000개 항목 조회 가능
- 총 3,219개 대여소 → 4페이지 필요
- 도로명 주소 기반 좌표 제공

---

### 2️⃣ 대여가능 자전거 현황 (`/inf_101_00010002_v2`)

각 대여소의 **현재 대여가능 자전거 수**를 제공합니다.

**엔드포인트**: `GET /inf_101_00010002_v2`

**요청 파라미터**

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `serviceKey` | string | 공공데이터포털 인증키 |
| `lcgvmnInstCd` | string | 지자체코드 (서울시) |
| `pageNo` | integer | 페이지 번호 |
| `numOfRows` | integer | 한 페이지 결과 수 |
| `type` | string | 응답 타입 |

**응답 항목**

| 필드 | 타입 | 설명 |
|-----|------|------|
| `rntstnId` | string | 대여소 ID |
| `rntstnNm` | string | 대여소명 |
| `lat` | decimal | 위도 |
| `lot` | decimal | 경도 |
| `bcyclTpkctNocs` | integer | **대여가능 자전거 수** (현재 반납된 자전거) |

**사용 예시**

```python
import requests

params = {
    'serviceKey': 'YOUR_API_KEY',
    'lcgvmnInstCd': '1100000000',
    'pageNo': 1,
    'numOfRows': 1000,
    'type': 'JSON'
}

response = requests.get(
    'https://apis.data.go.kr/B551982/pbdo_v2/inf_101_00010002_v2',
    params=params
)
data = response.json()

for item in data['body']['item']:
    available = item['bcyclTpkctNocs']
    print(f"{item['rntstnNm']}: 대여가능 {available}대")
```

**주의사항**
- 실시간으로 변동됨 (3분마다 수집 권장)
- 값이 0이면 대여 불가능
- 반납 가능 여부는 별도 필드 미제공 (master 정보에서 랙 수 확인)

---

### 3️⃣ 대여/반납 현황 (`/inf_101_00010003_v2`)

각 대여소의 **일일 대여/반납 건수 통계**를 제공합니다.

**엔드포인트**: `GET /inf_101_00010003_v2`

**요청 파라미터**

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `serviceKey` | string | 공공데이터포털 인증키 |
| `lcgvmnInstCd` | string | 지자체코드 (서울시) |
| `fromCrtrYmd` | string | 시작일자 (YYYYMMDD) |
| `toCrtrYmd` | string | 종료일자 (YYYYMMDD) |
| `pageNo` | integer | 페이지 번호 |
| `numOfRows` | integer | 한 페이지 결과 수 |
| `type` | string | 응답 타입 |

**응답 항목**

| 필드 | 타입 | 설명 |
|-----|------|------|
| `rntstnId` | string | 대여소 ID |
| `rntstnNm` | string | 대여소명 |
| `crtrYmd` | string | 통계 날짜 (YYYYMMDD) |
| `rntNocs` | integer | **해당 날짜 대여 건수** |
| `rtnNocs` | integer | **해당 날짜 반납 건수** |

**사용 예시**

```python
import requests
from datetime import datetime, timedelta

today = datetime.now().strftime('%Y%m%d')
yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')

params = {
    'serviceKey': 'YOUR_API_KEY',
    'lcgvmnInstCd': '1100000000',
    'fromCrtrYmd': yesterday,
    'toCrtrYmd': today,
    'pageNo': 1,
    'numOfRows': 1000,
    'type': 'JSON'
}

response = requests.get(
    'https://apis.data.go.kr/B551982/pbdo_v2/inf_101_00010003_v2',
    params=params
)
data = response.json()

for item in data['body']['item']:
    print(f"{item['rntstnNm']} ({item['crtrYmd']}): "
          f"대여 {item['rntNocs']}건, 반납 {item['rtnNocs']}건")
```

**비고**
- 일일 통계 데이터
- 날짜 범위는 최대 1개월까지 가능
- 현재 날짜 데이터는 당일 야간에만 제공됨

---

## 데이터 활용 사례

### 1. 대여소 마스터 데이터 적재 (1회)

```python
def seed_bike_stations(api_key: str):
    """강서구 자전거 대여소 정보를 master.bike_stations에 저장"""
    
    all_stations = fetch_all_bike_stations(api_key, '1100000000')
    
    # 강서구 좌표 범위로 필터링
    gangseo_stations = [
        s for s in all_stations
        if 37.53 <= float(s['lat']) <= 37.58
        and 126.80 <= float(s['lot']) <= 126.88
    ]
    
    for station in gangseo_stations:
        save_to_db({
            'station_id': station['rntstnId'],
            'station_name': station['rntstnNm'],
            'latitude': float(station['lat']),
            'longitude': float(station['lot']),
            'rack_count': estimate_rack_count(station),  # 별도 추정
        })
```

### 2. 실시간 대여가능 현황 수집 (3분마다)

```python
def collect_bike_availability(api_key: str, redis_client: redis.Redis):
    """현재 대여가능 자전거 수를 수집"""
    
    availability = fetch_bike_availability(api_key, '1100000000')
    
    for station in availability:
        station_id = station['rntstnId']
        available_bikes = int(station['bcyclTpkctNocs'])
        
        # Redis에 캐시 저장 (3분 유효)
        redis_client.setex(
            f"bike:avail:{station_id}",
            180,
            json.dumps({
                'available_bikes': available_bikes,
                'available_racks': estimate_available_racks(station_id, available_bikes)
            })
        )
        
        # DB에 저장
        save_availability_to_db(station_id, available_bikes)
```

### 3. 대여/반납 통계 분석

```python
def analyze_rental_trends(api_key: str, date_from: str, date_to: str):
    """기간별 대여소 사용 현황 분석"""
    
    stats = fetch_rental_stats(api_key, '1100000000', date_from, date_to)
    
    # 대여소별 총 대여/반납 집계
    station_totals = {}
    for record in stats:
        station_id = record['rntstnId']
        if station_id not in station_totals:
            station_totals[station_id] = {'rentals': 0, 'returns': 0}
        
        station_totals[station_id]['rentals'] += int(record['rntNocs'])
        station_totals[station_id]['returns'] += int(record['rtnNocs'])
    
    # 인기 있는 대여소 찾기
    popular = sorted(
        station_totals.items(),
        key=lambda x: x[1]['rentals'],
        reverse=True
    )[:10]
    
    return popular
```

### 4. 경로 계산 시 자전거 가용성 확인

```python
def check_bike_availability_on_route(start_station_id: str, redis_client: redis.Redis):
    """시작점 대여소의 자전거 가용성 확인"""
    
    cache_key = f"bike:avail:{start_station_id}"
    cached = redis_client.get(cache_key)
    
    if cached:
        data = json.loads(cached)
        return data['available_bikes'] > 0
    
    return None  # 캐시 없음, API 호출 필요
```

---

## Redis 캐시 구조

```
# 대여소별 현재 대여가능 자전거
bike:avail:{rntstnId} = {
  "available_bikes": 15,
  "available_racks": 8,
  "station_name": "108. 서교동 사거리"
}
# TTL: 180초 (3분)

# 강서구 전체 대여소 마스터 (초기 로드용)
bike:master:gangseo = [{
  "station_id": "ST-100",
  "station_name": "103. 반포대로",
  "latitude": 37.5509,
  "longitude": 126.8495,
  "rack_count": 25
}, ...]
# TTL: 86400초 (1일)
```

---

## 데이터베이스 스키마

### master.bike_stations

```sql
-- 강서구 대여소 목록
SELECT station_id, station_name, latitude, longitude, rack_count
FROM master.bike_stations
WHERE district = '강서구'
ORDER BY station_name;

-- 좌표 범위로 검색
SELECT *
FROM master.bike_stations
WHERE latitude BETWEEN 37.53 AND 37.58
  AND longitude BETWEEN 126.80 AND 126.88;
```

### realtime.bike_availability

```sql
-- 최신 대여가능 현황 (대여소별)
SELECT station_id, available_bikes, available_racks, collected_at
FROM realtime.bike_availability
WHERE collected_at > now() - INTERVAL '1 hour'
ORDER BY collected_at DESC
LIMIT 1;

-- 시간대별 추이
SELECT 
  DATE_TRUNC('hour', collected_at) as hour,
  AVG(available_bikes) as avg_bikes,
  MIN(available_bikes) as min_bikes,
  MAX(available_bikes) as max_bikes
FROM realtime.bike_availability
WHERE station_id = 'ST-100'
  AND collected_at > now() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC;
```

---

## 성능 최적화 팁

### 1. 페이지네이션
```python
# 서울시 전체: ~2,700~3,200개 대여소
# 한 번에 1000개씩 → 3~4페이지
for page in range(1, 5):
    fetch_page(page_no=page, num_of_rows=1000)
```

### 2. 수집 주기
- **마스터 데이터**: 1일 1회 (오전)
- **대여가능 현황**: 3분 간격 (06-23시)
- **대여/반납 통계**: 1일 1회 (야간)

### 3. 캐시 전략
- 마스터 데이터 → Redis TTL: 24시간
- 실시간 가용성 → Redis TTL: 3분
- DB에는 모두 저장 (히스토리 분석용)

### 4. 필터링
```python
# 강서구 범위
GANGSEO_LAT_MIN, GANGSEO_LAT_MAX = 37.53, 37.58
GANGSEO_LNG_MIN, GANGSEO_LNG_MAX = 126.80, 126.88
```

### 5. 에러 처리
```python
# 페이지 없음 (INFO-200) → 수집 종료
# 네트워크 오류 → 재시도 (exponential backoff)
# Redis 캐시 실패 → 로깅만 하고 계속 진행
```

---

## 주의사항

### API 제약사항
- 응답 지연: 1-3초
- 레이트 제한: 시간당 수천 건 (명시 안 함)
- 현재 시간 데이터: 최대 2-3시간 지연

### 데이터 정확도
- 대여가능 수: 실시간에 가까움 (수초 지연 가능)
- 대여/반납 통계: 1일 지연 (당일 데이터는 야간 제공)
- 대여소 정보: 분기별 업데이트

### 강서구 범위
```python
GANGSEO_LAT_MIN = 37.53   # 남쪽 (강남스타)
GANGSEO_LAT_MAX = 37.58   # 북쪽 (강서초)
GANGSEO_LNG_MIN = 126.80  # 서쪽 (명농로)
GANGSEO_LNG_MAX = 126.88  # 동쪽 (강변도로)
```

---

## 관련 파일

- `backend/app/collectors/bike_collector.py` - 자전거 데이터 수집기
- `backend/app/db/init.py` - DB 테이블 정의 (`master.bike_stations`, `realtime.bike_availability`)
- `backend/scripts/seed_master_data.py` - 마스터 데이터 초기 적재
