# TMAP 대중교통 경로 API 사용 가이드

## 개요

SK Telecom의 TMAP 대중교통 경로 API를 활용하여 출발지에서 목적지까지의 최적 대중교통 경로를 조회합니다. 버스, 지하철, 기차 등 다양한 대중교통 수단을 포함한 경로 정보를 반환합니다.

---

## API 기본 정보

**베이스 URL**: `https://apis.openapi.sk.com/transit/routes`

**요청 방식**: `POST` (JSON Body)

**인증**: `appKey` 헤더에 SKT 발급 App Key 필수

**응답 형식**: JSON

**무료 플랜**: 1,000건/일

---

## 엔드포인트 및 파라미터

### 요청 헤더

| 헤더명 | 필수 | 값 |
|--------|------|-----|
| `appKey` | ✅ | SKT 발급 App Key |
| `Content-Type` | ✅ | `application/json` |
| `accept` | - | `application/json` (기본값) |

### 요청 바디 파라미터

| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|---------|------|-----|------|------|
| `startX` | string | ✅ | 출발지 경도 (WGS84) | `"126.849"` |
| `startY` | string | ✅ | 출발지 위도 (WGS84) | `"37.557"` |
| `endX` | string | ✅ | 목적지 경도 (WGS84) | `"126.823"` |
| `endY` | string | ✅ | 목적지 위도 (WGS84) | `"37.545"` |
| `reqCoordType` | string | - | 요청 좌표계 (기본값: WGS84GEO) | `"WGS84GEO"` |
| `resCoordType` | string | - | 응답 좌표계 (기본값: WGS84GEO) | `"WGS84GEO"` |
| `count` | integer | - | 반환할 경로 수 (기본값: 3) | `1` |
| `lang` | string | - | 응답 언어 (기본값: ko) | `"ko"` |
| `format` | string | - | 응답 형식 (기본값: json) | `"json"` |

### 좌표계 설명

| 좌표계 | 설명 |
|--------|------|
| `WGS84GEO` | 위도/경도 (GPS 표준) — **권장** |
| `WGS84KATECH` | 카텍 좌표계 |
| `TM` | 중부원점 TM 좌표계 |

---

## 응답 구조

### 성공 응답 (HTTP 200)

```json
{
  "metaData": {
    "plan": {
      "itineraries": [
        {
          "fare": 2450,
          "duration": 1260,
          "transferCount": 1,
          "legs": [
            {
              "mode": "WALK",
              "sectionTime": 180,
              "distance": 250,
              "passShape": {
                "linestring": "126.849 37.557 126.851 37.556 126.852 37.555"
              },
              "start": {
                "name": "출발지",
                "latitude": 37.557,
                "longitude": 126.849
              },
              "end": {
                "name": "100번 버스 정류소",
                "latitude": 37.555,
                "longitude": 126.852
              }
            },
            {
              "mode": "BUS",
              "sectionTime": 840,
              "distance": 4200,
              "routeName": "100",
              "routeId": "1001",
              "passShape": {
                "linestring": "126.852 37.555 126.823 37.545"
              },
              "start": {
                "name": "함평터미널",
                "latitude": 37.555,
                "longitude": 126.852
              },
              "end": {
                "name": "목적지 근처",
                "latitude": 37.545,
                "longitude": 126.823
              }
            }
          ]
        }
      ]
    }
  }
}
```

### 응답 항목 설명

#### metaData.plan.itineraries[]

각 경로 정보

| 필드 | 타입 | 설명 |
|-----|------|------|
| `fare` | integer | 운임 (원) |
| `duration` | integer | 총 소요시간 (초) |
| `transferCount` | integer | 환승 횟수 (지하철/버스 기준) |
| `legs[]` | array | 이동 구간 배열 (도보/버스/지하철/기차 순서대로) |

#### legs[] — 각 구간 정보

| 필드 | 타입 | 설명 | 예시 |
|-----|------|------|------|
| `mode` | string | 이동 수단 | `WALK`, `BUS`, `SUBWAY`, `RAIL` |
| `sectionTime` | integer | 구간 소요시간 (초) | `180` |
| `distance` | integer | 구간 거리 (미터) | `250` |
| `routeName` | string | 노선 번호 (BUS/SUBWAY만) | `"100"`, `"2호선"` |
| `routeId` | string | 노선 ID (BUS/SUBWAY만) | `"1001"` |
| `passShape.linestring` | string | 좌표 경로 (공백/쉼표 구분) | 아래 참조 |
| `start` | object | 구간 시작지 (위도/경도/이름) | - |
| `end` | object | 구간 종료지 (위도/경도/이름) | - |

#### passShape.linestring 좌표 형식

`"경도1 위도1 경도2 위도2 경도3 위도3 ..."`

공백으로 구분된 위경도 쌍 (최대 수백 개 포인트)

**파싱 예시** (Python):
```python
linestring = "126.849 37.557 126.851 37.556 126.852 37.555"
coords = []
parts = linestring.split()
for i in range(0, len(parts), 2):
    lng, lat = float(parts[i]), float(parts[i+1])
    coords.append({"lng": lng, "lat": lat})
# coords = [{"lng": 126.849, "lat": 37.557}, ...]
```

---

## 사용 예시

### 1. Python httpx로 경로 조회

```python
import httpx
import json

async def fetch_tmap_route(start_lat, start_lng, end_lat, end_lng, app_key):
    """TMAP 대중교통 경로 조회"""
    
    url = "https://apis.openapi.sk.com/transit/routes"
    
    payload = {
        "startX": str(start_lng),
        "startY": str(start_lat),
        "endX": str(end_lng),
        "endY": str(end_lat),
        "reqCoordType": "WGS84GEO",
        "resCoordType": "WGS84GEO",
        "count": 3,  # 3가지 경로
    }
    
    headers = {
        "appKey": app_key,
        "Content-Type": "application/json",
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # 첫 번째 경로 추출
            itinerary = data["metaData"]["plan"]["itineraries"][0]
            print(f"소요시간: {itinerary['duration']}초 ({itinerary['duration']//60}분)")
            print(f"운임: {itinerary['fare']}원")
            print(f"환승: {itinerary['transferCount']}회")
            
            return itinerary
            
    except httpx.HTTPStatusError as e:
        print(f"TMAP API 오류: {e.response.status_code}")
        return None
```

### 2. 응답 파싱 — 경로 좌표 추출

```python
def parse_polyline_from_response(itinerary):
    """경로 이동선 좌표 목록 추출"""
    
    polyline = []
    
    for leg in itinerary.get("legs", []):
        linestring = leg.get("passShape", {}).get("linestring", "")
        
        if not linestring:
            continue
        
        # "경도 위도 경도 위도" 형식 파싱
        coords = linestring.split()
        for i in range(0, len(coords), 2):
            if i + 1 < len(coords):
                try:
                    lng = float(coords[i])
                    lat = float(coords[i + 1])
                    polyline.append({
                        "lng": lng,
                        "lat": lat
                    })
                except ValueError:
                    pass
    
    return polyline

# 사용
itinerary = fetch_tmap_route(37.557, 126.849, 37.545, 126.823, APP_KEY)
polyline = parse_polyline_from_response(itinerary)
print(f"경로 좌표 수: {len(polyline)}")
```

### 3. 구간별 이동 수단 및 시간 추출

```python
def analyze_legs(itinerary):
    """각 구간의 이동 수단, 거리, 시간 분석"""
    
    total_walk_dist = 0
    transfers = 0
    
    for leg in itinerary.get("legs", []):
        mode = leg.get("mode", "UNKNOWN")
        distance = leg.get("distance", 0)
        time_sec = leg.get("sectionTime", 0)
        
        if mode == "WALK":
            total_walk_dist += distance
            print(f"🚶 도보: {distance}m, {time_sec}초")
        
        elif mode == "BUS":
            print(f"🚌 버스 {leg.get('routeName', '?')}: {distance}m, {time_sec}초")
            transfers += 1
        
        elif mode == "SUBWAY":
            print(f"🚇 지하철 {leg.get('routeName', '?')}: {distance}m, {time_sec}초")
            transfers += 1
    
    print(f"\n총 도보거리: {total_walk_dist}m")
    print(f"총 환승: {transfers - 1}회")  # 첫 승차는 환승 아님

# 사용
analyze_legs(itinerary)
```

---

## 주의사항

### 1. 좌표 순서

- **요청**: X(경도), Y(위도)
- **응답**: linestring은 `"경도 위도 경도 위도"` 형식
- **Kakao Maps**: 일반적으로 `[위도, 경도]` 형식 — **반대 순서 주의**

### 2. 가능한 이동 수단 (mode)

| mode | 설명 |
|------|------|
| `WALK` | 도보 |
| `BUS` | 버스 (일반, 마을, 광역 포함) |
| `SUBWAY` | 지하철 |
| `RAIL` | 기차 (KTX, 일반열차 등) |
| `AIRPLANE` | 항공 (장거리 경로) |

### 3. 무료 플랜 제한

- **1일 1,000건 제한**
- 초과 시 HTTP 403 에러 반환
- 100m 그리드 기반 캐시 권장 (중복 요청 방지)

### 4. 시간 단위

- `duration`, `sectionTime`: **초(second)** 단위
- 분(minute) 필요 시: `/ 60` 계산

### 5. 에러 응답

```json
{
  "code": "04",
  "message": "잘못된 요청입니다",
  "currentDateTime": "2026-04-10T12:00:00+09:00"
}
```

**주요 에러 코드**

| code | 설명 |
|------|------|
| `01` | 정상 응답 |
| `04` | 잘못된 요청 (필수 파라미터 누락, 좌표 형식 오류) |
| `05` | API 호출 권한 없음 (App Key 미설정/만료) |
| `08` | 서버 오류 |
| `09` | 무료 이용량 초과 |

### 6. 좌표 범위 검증

TMAP은 한국 전역을 지원하지만, **서울 강서구**로 제한할 경우:

```python
GANGSEO_LAT_MIN = 37.53
GANGSEO_LAT_MAX = 37.58
GANGSEO_LNG_MIN = 126.80
GANGSEO_LNG_MAX = 126.88

def is_in_gangseo(lat, lng):
    return (GANGSEO_LAT_MIN <= lat <= GANGSEO_LAT_MAX and
            GANGSEO_LNG_MIN <= lng <= GANGSEO_LNG_MAX)
```

---

## 캐시 전략 (권장)

TMAP 1,000건/일 제한을 고려하여 그리드 캐시 적용:

| 캐시 타입 | 키 | TTL | 용도 |
|----------|-----|-----|------|
| 100m 그리드 | `tmap:grid:{lat}:{lng}` | 3,600초 | 근처 경로 겹침 제거 |
| 경로 전체 | `tmap:route:{start_hash}:{end_hash}` | 1,800초 | 동일 출도착 반복 요청 |

---

## 관련 코드 및 파일

- `backend/app/engine/route_finder.py:72-110` — TMAP API 호출 및 파싱
- `backend/app/config.py:17` — `tmap_app_key` 설정
- `.env` — `TMAP_APP_KEY` 환경변수

---

## 참고자료

- [TMAP 대중교통 API 공식 가이드](https://transit.tmapmobility.com/)
- [SK Open API 포털 — TMAP 대중교통](https://openapi.sk.com/products/detail?svcSeq=59)
- [TMAP 경로안내 샘플 예제](https://skopenapi.readme.io/reference/%EA%B2%BD%EB%A1%9C%EC%95%88%EB%82%B4-%EC%83%98%ED%94%8C%EC%98%88%EC%A0%9C)
