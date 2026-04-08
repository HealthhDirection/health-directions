/**
 * 추천 경로 2~3개 목록.
 *
 * props:
 *   routes         Array — scored route objects
 *   selectedIdx    number
 *   onSelect       (idx) => void
 *   loading        bool
 */

import RouteCard from "./RouteCard";

export default function RouteList({ routes = [], selectedIdx = 0, onSelect, loading }) {
  if (loading) {
    return (
      <div style={{ padding: 24, textAlign: "center", color: "#6b7280" }}>
        경로 탐색 중…
      </div>
    );
  }

  if (!routes.length) {
    return (
      <div style={{ padding: 24, textAlign: "center", color: "#6b7280" }}>
        경로를 찾을 수 없습니다.
      </div>
    );
  }

  return (
    <div>
      {routes.map((route, i) => (
        <RouteCard
          key={`${route.type}-${i}`}
          route={route}
          selected={i === selectedIdx}
          onClick={() => onSelect?.(i)}
        />
      ))}
    </div>
  );
}
