/**
 * Kakao Maps 래퍼 컴포넌트.
 * SDK는 index.html에서 script 태그로 로드.
 */

// TODO: Phase 4에서 구현
// - useEffect로 kakao.maps.Map 초기화
// - 강서구 중심 (lat: 37.5509, lng: 126.8495), 줌: 14
// - props: center, zoom, markers, polylines, onMapClick

export default function KakaoMap() {
  return <div id="kakao-map" style={{ width: "100%", height: "400px" }} />;
}
