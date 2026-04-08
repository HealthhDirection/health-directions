/**
 * 따릉이/버스 정류장 마커 데이터 생성 유틸.
 *
 * KakaoMap의 markers prop에 넘길 배열 항목을 만들어 준다:
 *   { lat, lng, label, color }
 */

/** 따릉이 대여소 마커 변환 */
export function toBikeMarkers(stations = []) {
  return stations.map((s) => {
    const bikes = s.available_bikes ?? 0;
    let color;
    if (bikes >= 3) color = "#16a34a";       // 초록 — 여유
    else if (bikes >= 1) color = "#d97706";  // 주황 — 주의
    else color = "#dc2626";                  // 빨강 — 없음

    return {
      lat: s.lat ?? s.latitude,
      lng: s.lng ?? s.longitude,
      label: `🚲 ${bikes}`,
      color,
    };
  });
}

/** 버스 정류장 마커 변환 */
export function toBusMarkers(stops = []) {
  return stops.map((s) => ({
    lat: s.lat ?? s.latitude,
    lng: s.lng ?? s.longitude,
    label: `🚌 ${s.stop_name ?? s.station_name ?? ""}`,
    color: "#1d4ed8",
  }));
}
