# 카카오맵 API 사용 가이드

## 개요

카카오 지도 Web API는 웹 페이지에 지도를 표시하고, 마커, 폴리라인 등을 추가하여 경로 정보를 시각화할 수 있습니다. 또한 Local API를 통해 주소-좌표 변환, 장소 검색 기능을 제공합니다.

본 프로젝트에서는:
- **지도 표시**: 강서구 중심 지도 생성
- **경로 시각화**: 추천 경로를 폴리라인으로 표시
- **마커 표시**: 출발지, 목적지, 버스/따릉이 정류소 마커
- **주소-좌표 변환**: 사용자 검색 주소 → 좌표 변환

---

## 1. API 키 발급

### 발급 절차

1. **카카오 개발자 사이트** 접속: `https://developers.kakao.com`
2. **회원가입/로그인**
3. **[My Application]** → **[애플리케이션 추가]**
   - 앱 이름: `Health Directions` (예시)
   - 사업자 정보: 선택 (개발용이면 안 함)
4. **[앱 설정]** → **[플랫폼]** → **Web**에서 **JavaScript 키** 복사
5. `.env`에 저장:
   ```env
   VITE_KAKAO_MAP_KEY=발급받은_JavaScript_키
   ```

### 주의사항

- **JavaScript 키**와 **REST API 키**는 다름
  - JavaScript 키: 프론트엔드 지도/마커 표시용 ✅
  - REST API 키: 백엔드 주소 검색용
- 프론트엔드는 JavaScript 키만 필요
- 본 프로젝트에서는 모든 좌표-주소 변환을 **클라이언트 사이드** `kakao.maps.services.Geocoder` API로 처리

---

## 2. SDK 초기화

### HTML에 스크립트 추가

`frontend/index.html`:

```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Health Directions</title>
    <!-- 카카오맵 SDK (필수) -->
    <script type="text/javascript" src="//dapi.kakao.com/v2/maps/sdk.js?appkey=발급받은_JavaScript_키&libraries=services,drawing"></script>
</head>
<body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
</body>
</html>
```

### 라이브러리 옵션

**libraries 파라미터:**

| 라이브러리 | 용도 |
|----------|------|
| `services` | 주소-좌표 변환, 장소 검색 (Geocoder) |
| `drawing` | 마커, 도형 그리기 (본 프로젝트 미사용) |
| `clusterer` | 마커 클러스터링 (미사용) |

---

## 3. 지도 생성 및 설정

### React 컴포넌트 예제

`frontend/src/components/Map/KakaoMap.jsx`:

```jsx
import { useEffect, useRef } from 'react';

const KakaoMap = ({ width = '100%', height = '100vh', center = { lat: 37.557, lng: 126.849 } }) => {
  const mapContainer = useRef(null);
  const mapRef = useRef(null);

  useEffect(() => {
    if (mapContainer.current) {
      // 지도 옵션 설정
      const options = {
        center: new window.kakao.maps.LatLng(center.lat, center.lng),
        level: 6,  // 줌 레벨 (1: 가장 확대, 14: 가장 축소)
      };

      // 지도 생성
      mapRef.current = new window.kakao.maps.Map(mapContainer.current, options);
    }
  }, [center]);

  return <div ref={mapContainer} style={{ width, height }} />;
};

export default KakaoMap;
```

### 지도 옵션 설명

| 옵션 | 타입 | 설명 | 기본값 |
|------|------|------|--------|
| `center` | LatLng | 지도 중심 좌표 | - |
| `level` | integer | 줌 레벨 (1~14) | 3 |
| `draggable` | boolean | 드래그 여부 | true |
| `scrollwheel` | boolean | 마우스휠 줌 여부 | true |
| `disableDoubleClick` | boolean | 더블클릭 줌 비활성화 | false |

### LatLng 객체 생성

```javascript
// 방법 1: 좌표로 생성
const position = new kakao.maps.LatLng(37.557, 126.849);

// 방법 2: 객체로 생성
const position = new kakao.maps.LatLng({
  lat: 37.557,
  lng: 126.849
});
```

**주의**: 위도(lat), 경도(lng) 순서 ⚠️

---

## 4. 마커(Marker) 표시

### 단일 마커 추가

```javascript
const marker = new kakao.maps.Marker({
  position: new kakao.maps.LatLng(37.557, 126.849),
  title: '출발지',  // 마우스 호버 시 보이는 텍스트
  image: new kakao.maps.MarkerImage(
    'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/markerStar.png',
    new kakao.maps.Size(24, 35)
  )
});

marker.setMap(map);  // 지도에 마커 표시
```

### 마커 배열 처리 (경로 상의 모든 마커)

```javascript
// 마커 목록 (예: 경로상 버스 정류소)
const stations = [
  { lat: 37.557, lng: 126.849, name: '강서구청', type: 'bus' },
  { lat: 37.551, lng: 126.835, name: '공항철도역', type: 'bike' },
];

const markers = stations.map(station => {
  const imageUrl = station.type === 'bus' 
    ? 'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/busMarker.png'
    : 'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/markerStar.png';

  return new kakao.maps.Marker({
    position: new kakao.maps.LatLng(station.lat, station.lng),
    title: station.name,
    image: new kakao.maps.MarkerImage(imageUrl, new kakao.maps.Size(24, 35))
  });
});

// 지도에 모두 표시
markers.forEach(marker => marker.setMap(map));

// 제거 (나중에 새로운 경로로 전환할 때)
markers.forEach(marker => marker.setMap(null));
```

### 내장 마커 타입

카카오 제공 기본 마커:
- `https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/markerStar.png` — 별 모양
- `https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/busMarker.png` — 버스 아이콘
- `https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/bikeMarker.png` — 자전거 아이콘

---

## 5. 폴리라인(Polyline) - 경로 표시

### 경로 폴리라인 그리기

```javascript
// TMAP에서 받은 polyline 좌표 배열
const routeCoords = [
  { lng: 126.849, lat: 37.557 },
  { lng: 126.848, lat: 37.556 },
  { lng: 126.847, lat: 37.555 },
  // ... 수백 개의 좌표
];

// LatLng 객체 배열로 변환
const polylinePath = routeCoords.map(coord => 
  new kakao.maps.LatLng(coord.lat, coord.lng)
);

// 폴리라인 생성
const polyline = new kakao.maps.Polyline({
  path: polylinePath,
  strokeColor: '#FF6200',  // 주황색
  strokeOpacity: 0.8,
  strokeWeight: 3,
  map: map
});
```

### 경로 타입별 스타일링

```javascript
function createPolyline(map, route) {
  let polylineStyle = {
    path: route.polyline.map(c => new kakao.maps.LatLng(c.lat, c.lng)),
    map: map
  };

  // 경로 타입에 따른 색상/두께 구분
  if (route.type === 'bus_only') {
    polylineStyle.strokeColor = '#FF6200';  // 주황색
    polylineStyle.strokeWeight = 3;
  } else if (route.type === 'bus_bike') {
    polylineStyle.strokeColor = '#00B050';  // 초록색
    polylineStyle.strokeWeight = 3;
  } else if (route.type === 'walk_bike') {
    polylineStyle.strokeColor = '#4472C4';  // 파란색
    polylineStyle.strokeWeight = 2;
  }

  return new kakao.maps.Polyline(polylineStyle);
}
```

### 폴리라인 옵션

| 옵션 | 타입 | 설명 |
|------|------|------|
| `path` | LatLng[] | 경로 좌표 배열 |
| `strokeColor` | string | 선 색상 (16진수 코드) |
| `strokeOpacity` | number | 투명도 (0.0 ~ 1.0) |
| `strokeWeight` | integer | 선 두께 (픽셀) |
| `strokeStyle` | string | `solid` / `shortdash` / `shortdot` 등 |
| `map` | Map | 지도 객체 (표시 대상) |

---

## 6. 주소-좌표 변환

### Geocoder API 초기화

```javascript
const geocoder = new kakao.maps.services.Geocoder();
```

### 주소 → 좌표 변환 (addressSearch)

```javascript
function searchAddressToCoord(address) {
  const geocoder = new kakao.maps.services.Geocoder();

  geocoder.addressSearch(address, function(result, status) {
    if (status === kakao.maps.services.Status.OK) {
      const coords = {
        lat: parseFloat(result[0].y),
        lng: parseFloat(result[0].x)
      };
      console.log(`주소 "${address}" → 좌표: ${coords.lat}, ${coords.lng}`);
      return coords;
    } else {
      console.error(`주소 검색 실패: ${status}`);
      return null;
    }
  });
}

// 사용 예
searchAddressToCoord('강서구청');
```

### 좌표 → 주소 변환 (coord2RegionCode, coord2Address)

```javascript
function searchCoordToAddress(lat, lng) {
  const geocoder = new kakao.maps.services.Geocoder();

  geocoder.coord2RegionCode(lng, lat, function(result, status) {
    if (status === kakao.maps.services.Status.OK) {
      const address = result[0].address_name;  // 행정구역명
      const region = result[0].region_1depth_name;  // 시/도
      const district = result[0].region_2depth_name;  // 구/군
      
      console.log(`좌표 (${lat}, ${lng}) → 주소: ${address}`);
      return { address, region, district };
    }
  });
}

// 도로명 주소 반환 (상세)
function searchCoordToRoadAddress(lat, lng) {
  const geocoder = new kakao.maps.services.Geocoder();

  geocoder.coord2Address(lng, lat, function(result, status) {
    if (status === kakao.maps.services.Status.OK) {
      const roadAddress = result[0].road_address?.address_name || '도로명 주소 없음';
      const jibunAddress = result[0].address?.address_name || '지번 주소 없음';
      
      console.log(`도로명: ${roadAddress}`);
      console.log(`지번: ${jibunAddress}`);
      return { roadAddress, jibunAddress };
    }
  });
}

// 사용
searchCoordToAddress(37.557, 126.849);
searchCoordToRoadAddress(37.557, 126.849);
```

### 장소 검색 (keywordSearch)

```javascript
function searchPlacesByKeyword(keyword) {
  const service = new kakao.maps.services.Places();

  service.keywordSearch(keyword, function(data, status, pagination) {
    if (status === kakao.maps.services.Status.OK) {
      data.forEach(place => {
        console.log(`장소: ${place.place_name}`);
        console.log(`  주소: ${place.address_name}`);
        console.log(`  좌표: (${place.y}, ${place.x})`);
      });
      return data;
    }
  });
}

// 사용
searchPlacesByKeyword('카페');
```

---

## 7. React 통합 예제 (완전한 예제)

### RouteMap.jsx

```jsx
import { useEffect, useRef } from 'react';
import { useRouteStore } from '../../store/routeStore';

const RouteMap = () => {
  const mapContainer = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef([]);
  const polylinesRef = useRef([]);
  
  const { routes, selectedRoute } = useRouteStore();

  useEffect(() => {
    // 지도 초기화 (한 번만)
    if (!mapRef.current && mapContainer.current) {
      const options = {
        center: new window.kakao.maps.LatLng(37.557, 126.849),
        level: 7,
      };
      mapRef.current = new window.kakao.maps.Map(mapContainer.current, options);
    }
  }, []);

  // 선택된 경로가 변경되면 표시 업데이트
  useEffect(() => {
    if (!mapRef.current || !selectedRoute) return;

    // 기존 마커/폴리라인 제거
    markersRef.current.forEach(m => m.setMap(null));
    polylinesRef.current.forEach(p => p.setMap(null));
    markersRef.current = [];
    polylinesRef.current = [];

    // 새 경로 폴리라인 추가
    if (selectedRoute.polyline && selectedRoute.polyline.length > 0) {
      const path = selectedRoute.polyline.map(
        c => new window.kakao.maps.LatLng(c.lat, c.lng)
      );
      const polyline = new window.kakao.maps.Polyline({
        path,
        strokeColor: '#FF6200',
        strokeWeight: 3,
        strokeOpacity: 0.8,
        map: mapRef.current
      });
      polylinesRef.current.push(polyline);
    }

    // 출발지/목적지 마커 추가
    if (selectedRoute.start) {
      const startMarker = new window.kakao.maps.Marker({
        position: new window.kakao.maps.LatLng(
          selectedRoute.start.lat,
          selectedRoute.start.lng
        ),
        title: '출발지',
        map: mapRef.current
      });
      markersRef.current.push(startMarker);
    }

    if (selectedRoute.end) {
      const endMarker = new window.kakao.maps.Marker({
        position: new window.kakao.maps.LatLng(
          selectedRoute.end.lat,
          selectedRoute.end.lng
        ),
        title: '목적지',
        map: mapRef.current
      });
      markersRef.current.push(endMarker);
    }

    // 지도 중심을 경로 중점으로 설정
    if (selectedRoute.polyline && selectedRoute.polyline.length > 0) {
      const mid = Math.floor(selectedRoute.polyline.length / 2);
      mapRef.current.setCenter(
        new window.kakao.maps.LatLng(
          selectedRoute.polyline[mid].lat,
          selectedRoute.polyline[mid].lng
        )
      );
    }
  }, [selectedRoute]);

  return (
    <div
      ref={mapContainer}
      style={{
        width: '100%',
        height: '600px',
        borderRadius: '8px',
        overflow: 'hidden'
      }}
    />
  );
};

export default RouteMap;
```

---

## 8. 줌 레벨 및 좌표 범위

### 줌 레벨별 보기 범위

| 레벨 | 설명 | 사용처 |
|------|------|--------|
| 1 | 전국 | - |
| 5 | 광역시/도 | 초기 지도 |
| 6-7 | 구/군 | 강서구 전체 보기 |
| 8-9 | 동/읍 | 경로 표시 시작 |
| 11-13 | 거리/블록 | 상세 경로 보기 |
| 14 | 건물 | 도보 경로 |

### 강서구 바운딩박스

```javascript
const gangseoNE = new kakao.maps.LatLng(37.58, 126.88);  // 북동쪽
const gangseoSW = new kakao.maps.LatLng(37.53, 126.80);  // 남서쪽

// 지도 경계 설정
const bounds = new kakao.maps.LatLngBounds(gangseoSW, gangseoNE);
map.setBounds(bounds);
```

---

## 9. 이벤트 처리

### 지도 클릭 이벤트

```javascript
kakao.maps.event.addListener(map, 'click', function(mouseEvent) {
  const latlng = mouseEvent.latLng;
  console.log(`클릭한 좌표: ${latlng.getLat()}, ${latlng.getLng()}`);
});
```

### 마커 클릭 이벤트

```javascript
kakao.maps.event.addListener(marker, 'click', function() {
  console.log(`마커 "${marker.getTitle()}" 클릭됨`);
});
```

### 지도 드래그 완료 이벤트

```javascript
kakao.maps.event.addListener(map, 'dragend', function() {
  const center = map.getCenter();
  console.log(`지도 중심 이동: ${center.getLat()}, ${center.getLng()}`);
});
```

---

## 10. 주의사항 및 팁

### ⚠️ 좌표 순서

| 상황 | 순서 | 예시 |
|------|------|------|
| Kakao API | 위도, 경도 | `LatLng(37.557, 126.849)` |
| TMAP API | 경도, 위도 | `startX: 126.849, startY: 37.557` |
| 응답 JSON | 변수명으로 확인 | `{lat: 37.557, lng: 126.849}` |

**자주하는 실수**: TMAP 응답의 `x, y`를 그대로 `LatLng(x, y)`에 넣으면 반대가 됨 ❌

### 성능 최적화

**많은 마커 표시 시:**
```javascript
// ❌ 비효율적
markers.forEach(m => m.setMap(map));  // 1개씩 추가

// ✅ 효율적
const layer = new kakao.maps.AbstractDrawingOverlay(map);
markers.forEach(m => layer.add(m));
```

**많은 폴리라인 단순화:**
```javascript
// Douglas-Peucker 알고리즘 등으로 포인트 수 줄이기
function simplifyPath(path, tolerance = 0.0001) {
  // 예: 원본 200개 포인트 → 20개로 축약
  return path.filter((_, i) => i % 10 === 0);
}
```

### 디버깅

```javascript
// 지도 상태 확인
console.log('지도 중심:', map.getCenter());
console.log('줌 레벨:', map.getLevel());
console.log('지도 경계:', map.getBounds());

// 마커 상태 확인
console.log('마커 위치:', marker.getPosition());
console.log('마커 제목:', marker.getTitle());
console.log('마커 표시 여부:', marker.getMap() !== null);
```

---

## 11. 관련 파일 및 참고자료

**프로젝트 파일:**
- `frontend/index.html` — SDK 로드
- `frontend/src/components/Map/KakaoMap.jsx` — 기본 지도 컴포넌트
- `frontend/src/components/Route/RouteMap.jsx` — 경로 표시 컴포넌트
- `frontend/src/utils/api.js` — API 호출

**공식 문서:**
- [Kakao 지도 Web API 가이드](https://apis.map.kakao.com/web/guide/)
- [Kakao Developers 문서](https://developers.kakao.com/docs/latest/ko/kakaomap/common)
- [Services API (Geocoder, Places)](https://developers.kakao.com/docs/latest/ko/local/dev-guide)
- [샘플 코드](https://apis.map.kakao.com/web/sample/)

**개발 팁:**
- [카카오 Maps API를 이용하여 경로 표시하기](https://velog.io/@hyunjoogo/%EC%B9%B4%EC%B9%B4%EC%98%A4-Maps-API%EB%A5%BC-%EC%9D%B4%EC%9A%A9%ED%95%98%EC%97%AC-%EA%B2%BD%EB%A1%9C-%ED%91%9C%EC%8B%9C%ED%95%98%EA%B8%B0)

---

## 12. 라이선스 및 약관

- **무료 플랜**: 월 100만 건의 지도/서비스 호출 제한
- **비즈니스 정보**: 카카오톡 채널 개설 시 비즈니스 정보 노출 가능 (선택사항)
- **이용약관**: Kakao Developers 이용약관 준수 필수

