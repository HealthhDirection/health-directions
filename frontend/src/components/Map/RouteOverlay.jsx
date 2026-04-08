/**
 * 경로 폴리라인 스타일 유틸.
 *
 * KakaoMap의 polylines prop에 넘길 배열 항목을 만들어 준다:
 *   { path, color, width, opacity }
 */

const ROUTE_COLORS = {
  bus_only:  "#2563eb",  // 파랑
  bus_bike:  "#16a34a",  // 초록
  walk_bike: "#d97706",  // 주황
};

/**
 * 경로 배열(scored routes)을 KakaoMap polylines prop 형식으로 변환한다.
 *
 * @param {Array}  routes          - /api/routes 응답의 routes 배열
 * @param {number} selectedIdx     - 선택된 경로 인덱스 (선택 경로는 더 굵게)
 */
export function toPolylines(routes = [], selectedIdx = 0) {
  return routes
    .filter((r) => r.polyline?.length > 0)
    .map((r, i) => {
      const isSelected = i === selectedIdx;
      return {
        path: r.polyline,
        color: ROUTE_COLORS[r.type] ?? "#6b7280",
        width: isSelected ? 6 : 3,
        opacity: isSelected ? 0.9 : 0.45,
      };
    });
}

/** 경로 타입 → 표시 이름 */
export function routeTypeLabel(type) {
  const map = {
    bus_only:  "버스",
    bus_bike:  "버스+따릉이",
    walk_bike: "도보+따릉이",
  };
  return map[type] ?? type;
}

/** 경로 타입 → CSS 클래스 */
export function routeTypeBadgeClass(type) {
  const map = {
    bus_only:  "badge-bus-only",
    bus_bike:  "badge-bus-bike",
    walk_bike: "badge-walk-bike",
  };
  return map[type] ?? "";
}
