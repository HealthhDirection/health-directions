/**
 * 단일 경로 요약 카드.
 *
 * props:
 *   route       object — /api/routes 응답의 경로 항목
 *   selected    bool
 *   onClick     () => void
 */

import BikeAvailability from "./BikeAvailability";
import { routeTypeLabel, routeTypeBadgeClass } from "../Map/RouteOverlay";

export default function RouteCard({ route, selected, onClick }) {
  const {
    type,
    estimated_duration_min,
    walk_dist_m = 0,
    bike_dist_m = 0,
    transfers = 0,
    bike_probability,
    bike_station,
    intersections = [],
  } = route;

  const durationMin = Math.round(estimated_duration_min ?? 0);
  const walkKm = (walk_dist_m / 1000).toFixed(1);
  const bikeKm = (bike_dist_m / 1000).toFixed(1);
  const hasSignal = intersections.length > 0;
  const hasBike = bike_dist_m > 0 && bike_probability != null;

  return (
    <div
      className={`route-card${selected ? " selected" : ""}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && onClick?.()}
    >
      <div className="route-card-header">
        <span className={`route-type-badge ${routeTypeBadgeClass(type)}`}>
          {routeTypeLabel(type)}
        </span>
        <div className="route-duration">
          {durationMin} <span>분</span>
        </div>
      </div>

      <div className="route-meta">
        {walk_dist_m > 0 && <span>도보 {walkKm}km</span>}
        {bike_dist_m > 0 && <span>자전거 {bikeKm}km</span>}
        {transfers > 0 && <span>환승 {transfers}회</span>}
      </div>

      <div className="route-badges">
        {hasSignal && (
          <span className="signal-badge">신호반영</span>
        )}
      </div>

      {hasBike && (
        <div style={{ marginTop: 8 }}>
          <BikeAvailability
            probability={bike_probability}
            stationName={bike_station?.station_name}
            ahead={durationMin}
          />
        </div>
      )}
    </div>
  );
}
