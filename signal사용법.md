# 신호등 데이터 API 사용 가이드

## 개요

공공데이터포털의 실시간 신호등 정보(RTI, Real Time Info) API를 활용하여 서울시 교차로의 신호 상태와 잔여시간을 수집합니다.

---

## API 기본 정보

**베이스 URL**: `https://apis.data.go.kr/B551982/rti`

**인증**: `serviceKey` 파라미터에 공공데이터포털 인증키 필수

**지자체 코드**: 서울시 = `1100000000`
- 현재 시(市) 단위 코드만 지원
- 강서구 코드 (`1150000000`)는 지원 안 함 → 서울 전체 조회 후 좌표 기반 필터링 필요

**응답 형식**: JSON

**주의**: 
- `mapCtptIntLot` (경도) 필드가 API에서 빈 값으로 반환됨
- TMAP Geocoding API로 보완해야 함

---

## 2가지 주요 엔드포인트

### 1️⃣ 교차로 위치 정보 (`/crsrd_map_info`)

서울시 모든 교차로의 ID, 이름, 위도 정보를 제공합니다.

**엔드포인트**: `GET /crsrd_map_info`

**요청 파라미터**

| 파라미터 | 타입 | 설명 | 예시 |
|---------|------|------|------|
| `serviceKey` | string | 공공데이터포털 인증키 | - |
| `stdgCd` | string | 지자체코드 (서울시) | `1100000000` |
| `pageNo` | integer | 페이지 번호 (기본값: 1) | `1` |
| `numOfRows` | integer | 한 페이지 결과 수 (기본값: 10) | `1000` |
| `type` | string | 응답 파일 타입 | `JSON` |

**응답 항목**

| 필드 | 타입 | 설명 |
|-----|------|------|
| `crsrdId` | string | 교차로 ID (PK) |
| `crsrdNm` | string | 교차로명 (예: "강남역") |
| `latitude` | decimal | 교차로 위도 |
| `mapCtptIntLat` | decimal | 교차로 위도 (대체) |
| `mapCtptIntLot` | decimal | 교차로 경도 ❌ (빈 값) |

**사용 예시**

```python
import requests

params = {
    'serviceKey': 'YOUR_API_KEY',
    'stdgCd': '1100000000',  # 서울시
    'pageNo': 1,
    'numOfRows': 1000,
    'type': 'JSON'
}

response = requests.get(
    'https://apis.data.go.kr/B551982/rti/crsrd_map_info',
    params=params
)
data = response.json()

for item in data['body']['items']['item']:
    print(f"교차로: {item['crsrdNm']}, ID: {item['crsrdId']}, "
          f"위도: {item['latitude']}")
```

**비고**
- 한 페이지에 최대 1000개 항목 조회 가능
- 경도(`mapCtptIntLot`) 미제공 → TMAP Geocoding으로 보완 필요

---

### 2️⃣ 교차로별 신호 잔여시간 (`/tl_drct_info`)

각 교차로의 8방향 신호 상태와 잔여시간을 제공합니다.

**엔드포인트**: `GET /tl_drct_info`

**요청 파라미터**

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `serviceKey` | string | 공공데이터포털 인증키 |
| `stdgCd` | string | 지자체코드 (서울시) |
| `pageNo` | integer | 페이지 번호 |
| `numOfRows` | integer | 한 페이지 결과 수 |
| `type` | string | 응답 타입 |

**응답 항목** (방향별 반복)

| 필드 | 설명 | 값 |
|-----|------|-----|
| `crsrdId` | 교차로 ID | - |
| `crsrdNm` | 교차로명 | - |
| `{dir}PdsgSttsNm` | 보행 신호 상태 | `protected-movement-allowed`, `stop-and-remain`, `protected-clearance` 등 |
| `{dir}PdsgRmndCs` | 보행 신호 잔여시간 | **데시초(1/10초)** 단위 정수 |
| `{dir}VhclSttsNm` | 차량 신호 상태 | - |
| `{dir}VhclRmndCs` | 차량 신호 잔여시간 | **데시초(1/10초)** 단위 정수 |

**8방향 접두사**

| 방향 | 코드 | 설명 |
|-----|------|------|
| 북쪽 (North) | `nt` | 거리명: N |
| 동쪽 (East) | `et` | 거리명: E |
| 남쪽 (South) | `st` | 거리명: S |
| 서쪽 (West) | `wt` | 거리명: W |
| 동북쪽 (NE) | `ne` | - |
| 동남쪽 (SE) | `se` | - |
| 서남쪽 (SW) | `sw` | - |
| 서북쪽 (NW) | `nw` | - |

**신호 상태 매핑**

| API 값 | 의미 | 앱 표시 |
|--------|------|---------|
| `protected-Movement-Allowed` | 진행 가능 (보호 신호) | 🟢 GREEN |
| `permissive-Movement-Allowed` | 진행 가능 (보조 신호) | 🟢 GREEN |
| `stop-And-Remain` | 정지 | 🔴 RED |
| `protected-clearance` | 클리어런스 (진행 후 정지 전) | 🟡 YELLOW |
| `permissive-clearance` | 클리어런스 (보조) | 🟡 YELLOW |
| (기타) | 알 수 없음 | ⚪ UNKNOWN |

**데시초 변환**

API는 **1/10초(데시초)** 단위로 반환합니다.

```
초 = int(데시초_값) / 10
예: 500 데시초 = 50초
```

**사용 예시**

```python
import requests

params = {
    'serviceKey': 'YOUR_API_KEY',
    'stdgCd': '1100000000',  # 서울시
    'pageNo': 1,
    'numOfRows': 100,
    'type': 'JSON'
}

response = requests.get(
    'https://apis.data.go.kr/B551982/rti/tl_drct_info',
    params=params
)
data = response.json()

# 8방향 신호 상태 추출
DIRECTIONS = ['nt', 'et', 'st', 'wt', 'ne', 'se', 'sw', 'nw']

for item in data['body']['items']['item']:
    crsrd_id = item['crsrdId']
    crsrd_nm = item['crsrdNm']
    
    for direction in DIRECTIONS:
        signal_status = item.get(f'{direction}PdsgSttsNm', '')
        remaining_decisec = item.get(f'{direction}PdsgRmndCs', '')
        
        if remaining_decisec:
            remaining_sec = int(remaining_decisec) // 10
            print(f"{crsrd_nm} - {direction}: {signal_status} ({remaining_sec}초)")
```

---

## 데이터 활용 사례

### 1. 교차로 마스터 데이터 적재

```python
def seed_intersections(api_key: str):
    """서울시 모든 교차로 정보를 master.intersections에 저장"""
    
    all_intersections = fetch_all_intersections(api_key)
    
    for item in all_intersections:
        intersection_id = item['crsrdId']
        intersection_name = item['crsrdNm']
        latitude = float(item['latitude'])
        
        # 경도는 미제공이므로 TMAP Geocoding으로 보충
        longitude = geocode_with_tmap(intersection_name)
        
        save_to_db(intersection_id, intersection_name, latitude, longitude)
```

### 2. 경로 계산 시 신호 대기시간 포함

```python
def estimate_crossing_time(intersection_id: str, redis_client: redis.Redis):
    """교차로 통과 시간 = 신호 잔여시간 + 안전 마진"""
    
    # Redis에서 최신 신호 상태 조회 (200초 캐시)
    signal_data = redis_client.get(f"signal:{intersection_id}")
    if not signal_data:
        return 10  # 기본값
    
    item = json.loads(signal_data)
    
    # 남쪽 방향 신호 확인 (예시)
    remaining_decisec = item.get('stPdsgRmndCs', 0)
    remaining_sec = int(remaining_decisec) // 10
    
    # 신호가 진행 중이면 잔여시간 반환, 정지 중이면 대기시간 추가
    return remaining_sec + 5  # 5초 안전 마진
```

### 3. 실시간 신호등 지도 표시

```javascript
// React/JavaScript에서 신호등 상태 표시

const signalColors = {
  'GREEN': '#00FF00',
  'RED': '#FF0000',
  'YELLOW': '#FFD700',
  'UNKNOWN': '#808080'
};

const SignalMarker = ({ intersection, signal }) => {
  return (
    <Marker
      position={[intersection.latitude, intersection.longitude]}
      icon={createIcon(signalColors[signal.current_phase])}
      title={`${intersection.name}: ${signal.remaining_sec}초`}
    />
  );
};
```

---

## Redis 캐시 구조

```
# 교차로별 신호 상태 (raw API 응답)
signal:{crsrdId} = {
  "crsrdId": "101",
  "crsrdNm": "강남역",
  "ntPdsgSttsNm": "protected-movement-allowed",
  "ntPdsgRmndCs": "450",  # 45초
  "etPdsgSttsNm": "stop-and-remain",
  "etPdsgRmndCs": "200",  # 20초
  ...
}
# TTL: 200초 (3분 수집 주기)
```

---

## 데이터베이스 스키마

### master.intersections

```sql
SELECT intersection_id, intersection_name, latitude, longitude
FROM master.intersections
WHERE longitude IS NOT NULL  -- 경도가 있는 교차로만
ORDER BY intersection_id;
```

**주의**: 
- 초기 적재 시 `longitude`는 NULL
- TMAP Geocoding으로 보완 시 UPDATE 필요

### realtime.signal_state

```sql
-- 특정 교차로 최신 신호 (8방향)
SELECT direction, current_phase, remaining_sec, collected_at
FROM realtime.signal_state
WHERE intersection_id = '101'
ORDER BY collected_at DESC
LIMIT 8;

-- 방향별 신호 상태 조회
SELECT *
FROM realtime.signal_state
WHERE intersection_id = '101'
AND direction = 'nt'  -- 북쪽
AND collected_at > now() - INTERVAL '5 minutes';
```

---

## 성능 최적화 팁

### 1. 페이지네이션 활용
```python
# 서울시 전체 교차로: ~5000개
# 한 번에 1000개씩 조회 → 5페이지
for page in range(1, 6):
    fetch_page(page_no=page, num_of_rows=1000)
```

### 2. 캐시 전략
- 마스터 데이터 (교차로 목록) → TTL: 24시간
- 신호 상태 → TTL: 200초 (3분 수집 주기)

### 3. 필터링
```python
# 강서구만 필터링 (좌표 기반)
GANGSEO_LAT_MIN, GANGSEO_LAT_MAX = 37.53, 37.58
GANGSEO_LNG_MIN, GANGSEO_LNG_MAX = 126.80, 126.88

intersections = [
    item for item in all_items
    if GANGSEO_LAT_MIN <= float(item['latitude']) <= GANGSEO_LAT_MAX
    and GANGSEO_LNG_MIN <= float(item.get('longitude', 0)) <= GANGSEO_LNG_MAX
]
```

### 4. 에러 처리
```python
# API 호출 실패 시 Redis 캐시 활용 (TTL 연장)
# 재시도: exponential backoff (2s → 4s → 8s)
```

---

## 주의사항

### API 제약사항
- 경도(`mapCtptIntLot`) 미제공 → 별도 Geocoding 필요
- 구(區) 단위 필터 미지원 → 서울 전체 조회 후 필터링
- 응답 지연: 2-5초

### 데이터 정확도
- 신호 상태는 수집 시점 기준
- 교차로에 따라 신호 주기 다름 (40~120초)
- 8방향이 모두 데이터를 제공하지는 않음 (방향별 신호 설치 현황에 따라)

### 강서구 범위
```python
GANGSEO_LAT_MIN = 37.53   # 남쪽
GANGSEO_LAT_MAX = 37.58   # 북쪽
GANGSEO_LNG_MIN = 126.80  # 서쪽
GANGSEO_LNG_MAX = 126.88  # 동쪽
```

---

## 관련 파일

- `backend/app/collectors/signal_collector.py` - 신호등 데이터 수집기
- `backend/app/db/init.py` - DB 테이블 정의
- `backend/scripts/seed_master_data.py` - 마스터 데이터 초기 적재
- `CLAUDE.md` - 신호등 DB 스키마 및 사용법
