# 건강길찾기 — 프론트엔드 현황

## 파일 구조

```
frontend/
├── vite.config.js          — Vite 설정, /api → localhost:8000 프록시, envDir: ".."
├── package.json            — React 18, react-router-dom 6, zustand 4, axios 1
├── src/
│   ├── main.jsx            — ReactDOM.createRoot, index.css 로드
│   ├── App.jsx             — BrowserRouter, / → HomePage, /routes → RoutePage
│   ├── index.css           — 전체 CSS (모바일 우선, 데스크탑 768px+ 분기)
│   ├── store/
│   │   └── routeStore.js   — zustand: origin, destination, routes[], loading
│   ├── utils/
│   │   └── api.js          — axios baseURL="/api", timeout 10s
│   ├── pages/
│   │   ├── HomePage.jsx    — 지도 + 검색 패널 + 따릉이/버스 레이어 토글
│   │   └── RoutePage.jsx   — 지도(55%) + 경로 목록 패널
│   └── components/
│       ├── Map/
│       │   ├── KakaoMap.jsx      — Kakao SDK 동적 로드, 마커·폴리라인 동기화
│       │   ├── RouteOverlay.jsx  — toPolylines() 유틸 (경로 → polylines prop)
│       │   └── StationMarker.jsx — toBikeMarkers(), toBusMarkers() 유틸
│       ├── Search/
│       │   └── SearchBar.jsx     — PlaceInput (Kakao Places 자동완성) + 검색 버튼
│       └── Route/
│           ├── RouteList.jsx     — 경로 목록 (로딩/빈 상태 처리)
│           ├── RouteCard.jsx     — 단일 경로 요약 (배지, 시간, 메타, 신호반영)
│           └── BikeAvailability.jsx — 따릉이 가용 확률 게이지 (0~1 → %)
```

---

## 각 컴포넌트 현황

### KakaoMap.jsx
- SDK를 `<script data-kakao-maps>` 태그로 동적 로드, 중복 방지 로직 있음
- `window.kakao.maps.load(callback)` 패턴으로 autoload=false 사용
- 마커: label 있으면 `CustomOverlay`, 없으면 `Marker`
- 폴리라인: `strokeWeight`, `strokeColor`, `strokeOpacity` 지원
- **알려진 제약**: SDK 초기화는 마운트 1회만 (deps `[]`). `center` prop 변경 시 지도 재중심 안됨. `fitBounds` 없어서 경로 전체가 화면에 맞지 않을 수 있음.

### RoutePage.jsx
- URL 파라미터(`olat`, `olng`, `dlat`, `dlng`)에서 좌표 추출
- `GET /api/routes` 호출 → `routeStore.setRoutes()`
- 지도 중심: 출발·도착 중간점
- 출발(초록)/도착(빨강) 핀 마커 + 선택 경로의 따릉이 마커 표시
- 503 에러 시 별도 메시지

### HomePage.jsx
- 따릉이 레이어: 기본 ON (앱 시작 시 `/api/stations/bike` 호출)
- 버스 레이어: 기본 OFF (버튼 토글 시 호출)
- 범례: 초록(3대+) / 주황(1~2대) / 빨강(0대)

### SearchBar.jsx
- `PlaceInput` 내부 컴포넌트: `window.kakao.maps.services.Places().keywordSearch()` 사용
- 최대 5개 제안, 외부 클릭 시 드롭다운 닫힘
- **알려진 제약**: `value` prop이 외부에서 바뀌어도 내부 `query` state가 동기화되지 않음 (홈으로 돌아왔을 때 이전 입력값이 표시 안 됨)

### RouteCard.jsx
- 경로 타입: `bus_only`(파랑 배지) / `bus_bike`(초록) / `walk_bike`(주황)
- 신호반영 뱃지: `intersections.length > 0` 일 때 표시
- BikeAvailability: `bike_dist_m > 0 && bike_probability != null` 일 때 표시

### RouteOverlay.jsx (유틸)
- 선택 경로: width 6, opacity 0.9 / 미선택: width 3, opacity 0.45
- 색상: bus_only `#2563eb` / bus_bike `#16a34a` / walk_bike `#d97706`

---

## 레이아웃 (index.css)

| 화면 | 홈 | 경로 페이지 |
|------|----|------------|
| 모바일 (<768px) | 지도 flex:1 (상단) + 검색 패널 (하단 고정) | 지도 55% (상단) + 경로 목록 (하단 스크롤) |
| 데스크탑 (≥768px) | 지도 flex:1 (좌) + 검색 패널 360px (우) | 지도 60% (좌) + 경로 목록 40% (우) |

---

## 현재 알려진 문제 / 개선 필요 사항

### 1. 지도 자동 범위 조정 없음
- 경로 폴리라인이 표시되지만, 출발지·도착지가 화면 밖으로 나갈 수 있음
- `kakao.maps.Map.setBounds()` 또는 `LatLngBounds`로 fitBounds 구현 필요

### 2. KakaoMap center prop 무시
- `useEffect(init, [])` 로 지도를 1회만 초기화하므로, `center` prop이 바뀌어도 지도가 이동하지 않음
- 별도 `useEffect([center])` 에서 `map.setCenter()` 호출 추가 필요

### 3. SearchBar 값 유지 안 됨
- 홈 → 경로 페이지 → 뒤로가기 시, zustand store에 origin/destination은 남아 있지만 input에 표시 안 됨
- `PlaceInput`의 초기 `query` state를 `value?.name ?? ""` 로 설정하므로 마운트 시 1회만 반영됨
- `useEffect([value], () => setQuery(value?.name ?? ""))` 추가 필요

### 4. 경로 없음 vs 로딩 중 UX
- API 호출 전 짧은 순간에 "경로를 찾을 수 없습니다" 메시지가 보일 수 있음 (`loading` false, `routes` empty 초기상태)
- `loading` 초기값을 `false`가 아닌 `null`로 구분하거나, URL 파라미터 존재 시 즉시 `true`로 세팅하도록 수정 고려

### 5. 지도 컨테이너 크기 문제
- `route-map-area`가 `height: 55%`로 고정되어 있어서, 경로 카드가 많으면 목록이 충분히 안 보임
- 패널 최소/최대 높이 또는 드래그 조절 UI 고려

### 6. 버스 정류장 마커 과밀
- 강서구 전체 버스 정류장을 한 번에 로드하면 수백 개 마커로 지도가 느려질 수 있음
- 줌 레벨에 따른 클러스터링 또는 뷰포트 내 필터링 고려

---

## 환경 변수

| 변수명 | 설명 | 위치 |
|--------|------|------|
| `VITE_KAKAO_MAP_KEY` | 카카오 지도 앱키 | 루트 `.env` |

`vite.config.js`에서 `envDir: ".."` 으로 루트 `.env`를 사용.

---

## API 연동 현황

| 엔드포인트 | 호출 위치 | 응답 사용 |
|-----------|----------|----------|
| `GET /api/routes` | `RoutePage.jsx` | `routes[]` → RouteList, polylines, bikeMarkers |
| `GET /api/stations/bike` | `HomePage.jsx` | `stations[]` → toBikeMarkers() |
| `GET /api/stations/bus` | `HomePage.jsx` | `stops[]` → toBusMarkers() |
