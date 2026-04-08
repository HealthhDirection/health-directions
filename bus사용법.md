# 버스 데이터 API 사용 가이드

## 개요

공공데이터포털의 버스 운영 데이터 API를 활용하여 강서구의 버스 노선, 정류소, 실시간 위치 정보를 수집합니다.

---

## API 기본 정보

**베이스 URL**: `https://apis.data.go.kr/B551982/rte`

**인증**: `serviceKey` 파라미터에 공공데이터포털 인증키 필수

**지자체 코드**: 강서구 = `1150000000`
- 시(市) 단위 코드만 지원 (구 단위 지원 안 함)
- 서울시 = `1100000000`

**응답 형식**: JSON

---

## 3가지 주요 엔드포인트

### 1️⃣ 노선 기본 정보 (`/mst_info`)

버스가 운행하는 노선의 기본 정보를 제공합니다.

**엔드포인트**: `GET /mst_info`

**요청 파라미터**

| 파라미터 | 타입 | 설명 | 예시 |
|---------|------|------|------|
| `serviceKey` | string | 공공데이터포털 인증키 | - |
| `stdgCd` | string | 지자체코드 (강서구) | `1150000000` |
| `pageNo` | integer | 페이지 번호 (기본값: 1) | `1` |
| `numOfRows` | integer | 한 페이지 결과 수 (기본값: 10) | `100` |
| `type` | string | 응답 파일 타입 (기본값: JSON) | `JSON` |

**응답 항목**

| 필드 | 타입 | 설명 |
|-----|------|------|
| `rteId` | string | 노선 ID (PK) |
| `rteNo` | string | 노선 번호 (예: "100", "500") |
| `rteType` | string | 노선 유형 (좌석버스, 일반버스 등) |
| `stpnt` | string | 기점 정류소명 |
| `edpnt` | string | 종점 정류소명 |
| `vhclFstTm` | string | 첫차 운행 시간 (HHMM, 예: "0605") |
| `vhclLstTm` | string | 막차 운행 시간 (HHMM, 예: "2300") |

**사용 예시**

```python
import requests

params = {
    'serviceKey': 'YOUR_API_KEY',
    'stdgCd': '1150000000',  # 강서구
    'pageNo': 1,
    'numOfRows': 100,
    'type': 'JSON'
}

response = requests.get('https://apis.data.go.kr/B551982/rte/mst_info', params=params)
data = response.json()

for item in data['body']['items']['item']:
    print(f"노선: {item['rteNo']}, 유형: {item['rteType']}, "
          f"기점: {item['stpnt']}, 종점: {item['edpnt']}")
```

**비고**
- 한 페이지에 최대 100개 항목 조회 가능
- 강서구는 구 단위 지원 안 되므로 `stdgCd=1150000000`으로 서울 전역 데이터 조회 후 필터링 필요

---

### 2️⃣ 노선 경유지 정보 (`/ps_info`)

버스 노선이 경유하는 정류소 목록과 좌표를 제공합니다.

**엔드포인트**: `GET /ps_info`

**요청 파라미터**

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `serviceKey` | string | 공공데이터포털 인증키 |
| `stdgCd` | string | 지자체코드 |
| `pageNo` | integer | 페이지 번호 |
| `numOfRows` | integer | 한 페이지 결과 수 |
| `type` | string | 응답 타입 |

**응답 항목**

| 필드 | 타입 | 설명 |
|-----|------|------|
| `rteId` | string | 노선 ID |
| `bstaId` | string | 정류소 ID (PK) |
| `bstaNm` | string | 정류소명 (예: "함평터미널") |
| `bstaNo` | string | 정류소 번호 |
| `bstaSn` | integer | 정류소 순번 (1, 2, 3, ...) |
| `bstaLat` | decimal | 정류소 위도 |
| `bstaLot` | decimal | 정류소 경도 |
| `drcGbnCd` | string | 방향 코드 ("0": 편도, "1": 상행, "2": 하행 등) |

**사용 예시**

```python
params = {
    'serviceKey': 'YOUR_API_KEY',
    'stdgCd': '1150000000',
    'pageNo': 1,
    'numOfRows': 100,
    'type': 'JSON'
}

response = requests.get('https://apis.data.go.kr/B551982/rte/ps_info', params=params)
data = response.json()

# 노선별 정류소 그룹화
stops_by_route = {}
for item in data['body']['items']['item']:
    rte_id = item['rteId']
    if rte_id not in stops_by_route:
        stops_by_route[rte_id] = []
    
    stops_by_route[rte_id].append({
        'name': item['bstaNm'],
        'sequence': item['bstaSn'],
        'lat': float(item['bstaLat']),
        'lng': float(item['bstaLot'])
    })
```

**비고**
- 총 5280개 항목 (여러 페이지 필요)
- `bstaSn`으로 정류소 순번 알 수 있음 (경로 매칭에 유용)
- 좌표 기반 지도 표시 및 경로 매칭에 활용

---

### 3️⃣ 버스 실시간 위치 정보 (`/rtm_loc_info`)

현재 운행 중인 버스의 GPS 기반 실시간 위치, 속도, 방향을 제공합니다.

**엔드포인트**: `GET /rtm_loc_info`

**요청 파라미터**

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `serviceKey` | string | 공공데이터포털 인증키 |
| `stdgCd` | string | 지자체코드 |
| `pageNo` | integer | 페이지 번호 |
| `numOfRows` | integer | 한 페이지 결과 수 |
| `type` | string | 응답 타입 |

**응답 항목**

| 필드 | 타입 | 설명 |
|-----|------|------|
| `rteId` | string | 노선 ID |
| `vhclNo` | string | 버스 차량번호 |
| `rteNo` | string | 노선 번호 (예: "100", "500") |
| `lat` | decimal | 버스의 현재 위도 |
| `lot` | decimal | 버스의 현재 경도 |
| `oprDrct` | string | 운행 방향각 (0-360도) |
| `oprSpd` | string | 운행 속도 (km/h) |
| `gthrDt` | string | 데이터 수집 시간 (ISO 8601, 예: "2026-04-08 00:00:00") |
| `evtType` | string | 이벤트 타입 ("GPS": GPS 신호) |
| `evtCd` | string | 이벤트 코드 (정상 운행 시 빈 값) |

**사용 예시**

```python
import requests
from datetime import datetime

params = {
    'serviceKey': 'YOUR_API_KEY',
    'stdgCd': '1150000000',
    'pageNo': 1,
    'numOfRows': 50,
    'type': 'JSON'
}

response = requests.get('https://apis.data.go.kr/B551982/rte/rtm_loc_info', params=params)
data = response.json()

# 버스별 위치 정보 정리
bus_locations = {}
for item in data['body']['items']['item']:
    vehicle_no = item['vhclNo']
    bus_locations[vehicle_no] = {
        'route_no': item['rteNo'],
        'location': {
            'lat': float(item['lat']),
            'lng': float(item['lot'])
        },
        'direction_angle': int(item['oprDrct']),
        'speed_kmh': int(item['oprSpd']),
        'collected_at': item['gthrDt']
    }

print(f"수집된 버스 수: {len(bus_locations)}")
```

**주의사항**
- 데이터가 실시간이 아니라 최근 수집한 데이터 (2-5분 지연)
- 각 요청마다 호출 제한 있음 (API 명세 참조)
- `oprDrct`: 0도 = 북쪽, 90도 = 동쪽, 180도 = 남쪽, 270도 = 서쪽

---

## 데이터 활용 사례

### 1. 버스 경로 수집 및 저장

```python
def collect_bus_routes(api_key: str):
    """강서구 버스 노선 및 정류소 정보를 DB에 저장"""
    
    # Step 1: 노선 기본 정보 조회
    routes = fetch_route_info(api_key)
    
    for route in routes:
        # Step 2: 각 노선의 정류소 조회
        stops = fetch_stops_for_route(api_key, route['rteId'])
        
        # Step 3: DB에 저장
        save_route_to_db(route, stops)
```

### 2. 실시간 버스 위치 추적

```python
def track_buses_realtime(api_key: str):
    """실시간으로 버스 위치를 조회하고 Redis에 캐시"""
    
    locations = fetch_bus_locations(api_key)
    
    for bus in locations:
        cache_key = f"bus:loc:{bus['vhclNo']}"
        redis_client.setex(
            cache_key,
            ttl=60,  # 60초 유효
            value=json.dumps({
                'lat': bus['lat'],
                'lng': bus['lot'],
                'speed': bus['oprSpd'],
                'direction': bus['oprDrct']
            })
        )
```

### 3. 경로 거리 및 도착시간 계산

```python
def estimate_arrival_time(start_lat, start_lng, end_lat, end_lng):
    """
    1. 버스 경로 데이터로 경로 내 모든 정류소 확인
    2. 현재 버스 위치로부터 가장 가까운 정류소 찾기
    3. 정류소 간 거리 + 현재 속도로 도착 예상시간 계산
    """
    pass
```

---

## Redis 캐시 구조 (제안)

```
# 노선 정보
route:{rteId} = {rteNo, rteType, stpnt, edpnt, ...}  # TTL: 86400 (1일)

# 정류소 목록
route:{rteId}:stops = [{bstaNm, bstaLat, bstaLot, bstaSn}, ...]  # TTL: 86400

# 버스 실시간 위치
bus:loc:{vhclNo} = {lat, lng, speed, direction, route_no}  # TTL: 120 (2분)

# 정류소별 버스 위치 (역색인)
stop:{bstaId}:buses = [{vhclNo, arrival_estimate}, ...]  # TTL: 60
```

---

## 성능 최적화 팁

1. **페이지네이션 활용**
   - 한 번에 모든 데이터를 조회하지 말고 `numOfRows=100`, `pageNo` 증가
   - 병렬 처리 시 API 호출 레이트 제한 주의

2. **캐시 활용**
   - 변하지 않는 데이터 (노선, 정류소 목록) → 1일 TTL
   - 자주 변하는 데이터 (버스 위치) → 60-120초 TTL

3. **증분 수집**
   - 초기: 전체 데이터 수집 (1시간 소요 가능)
   - 이후: 실시간 위치만 수집 (30초마다)

4. **에러 처리**
   - API 호출 실패 시 Redis 캐시 활용 (TTL 연장)
   - 재시도는 exponential backoff 사용

---

## 관련 파일

- `backend/app/collectors/bus_collector.py` - 버스 데이터 수집기
- `backend/scripts/seed_master_data.py` - 마스터 데이터 초기 적재
- `backend/app/db/schema.sql` - DB 테이블 정의
