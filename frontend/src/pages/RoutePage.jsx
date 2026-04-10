/**
 * 경로 결과 페이지 — 지도(상단) + 경로 목록(하단)
 * 데스크탑: 좌우 분할 (map 60% / list 40%)
 */

import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import KakaoMap from "../components/Map/KakaoMap";
import RouteList from "../components/Route/RouteList";
import { toPolylines } from "../components/Map/RouteOverlay";
import { toBikeMarkers } from "../components/Map/StationMarker";
import useRouteStore from "../store/routeStore";
import api from "../utils/api";

export default function RoutePage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const { origin, destination, routes, loading, setRoutes, setLoading } = useRouteStore();
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [error, setError] = useState(null);

  // URL 파라미터에서 좌표 추출
  const olat = parseFloat(searchParams.get("olat"));
  const olng = parseFloat(searchParams.get("olng"));
  const dlat = parseFloat(searchParams.get("dlat"));
  const dlng = parseFloat(searchParams.get("dlng"));

  // 경로 조회
  useEffect(() => {
    if (!olat || !olng || !dlat || !dlng) return;

    setLoading(true);
    setError(null);

    api
      .get("/routes", { params: { origin_lat: olat, origin_lng: olng, dest_lat: dlat, dest_lng: dlng } })
      .then((res) => {
        setRoutes(res.data.routes ?? []);
      })
      .catch((err) => {
        const msg =
          err.response?.status === 503
            ? "서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요."
            : "경로 조회 중 오류가 발생했습니다.";
        setError(msg);
        setRoutes([]);
      });
  }, [olat, olng, dlat, dlng]); // eslint-disable-line react-hooks/exhaustive-deps

  // 선택된 경로의 폴리라인 + 따릉이 마커
  const polylines = toPolylines(routes, selectedIdx);

  const selectedRoute = routes[selectedIdx];
  const bikeMarkers = selectedRoute?.bike_station
    ? toBikeMarkers([
        {
          lat: selectedRoute.bike_station.latitude,
          lng: selectedRoute.bike_station.longitude,
          station_name: selectedRoute.bike_station.station_name,
          available_bikes: selectedRoute.bike_station.available_bikes ?? 0,
        },
      ])
    : [];

  // 출발/도착 마커
  const pinMarkers = [
    olat && { lat: olat, lng: olng, label: "출발", color: "#16a34a" },
    dlat && { lat: dlat, lng: dlng, label: "도착", color: "#dc2626" },
  ].filter(Boolean);

  const allMarkers = [...pinMarkers, ...bikeMarkers];

  // 지도 중심 — 출발·도착 중간
  const mapCenter =
    olat && dlat
      ? { lat: (olat + dlat) / 2, lng: (olng + dlng) / 2 }
      : undefined;

  return (
    <div className="route-page">
      {/* 지도 영역 */}
      <div className="route-map-area">
        <KakaoMap
          center={mapCenter}
          zoom={7}
          markers={allMarkers}
          polylines={polylines}
        />
      </div>

      {/* 경로 목록 */}
      <div className="route-list-area">
        <div className="route-list-header">
          <button
            className="route-list-back"
            onClick={() => navigate("/")}
            aria-label="뒤로가기"
          >
            ←
          </button>
          <span className="route-list-title">
            {origin?.name && destination?.name
              ? `${origin.name} → ${destination.name}`
              : "경로 추천 결과"}
          </span>
        </div>

        {error ? (
          <div style={{ padding: "24px 16px", color: "#dc2626", fontSize: 13 }}>
            ⚠️ {error}
          </div>
        ) : (
          <RouteList
            routes={routes}
            selectedIdx={selectedIdx}
            onSelect={setSelectedIdx}
            loading={loading}
          />
        )}

        {/* 데이터 기준 안내 */}
        {!loading && routes.length > 0 && (
          <div
            style={{
              padding: "10px 16px",
              fontSize: 11,
              color: "#9ca3af",
              borderTop: "1px solid #f3f4f6",
            }}
          >
            * 소요시간은 추정값이며 신호 잔여시간이 반영된 경로는 <strong>신호반영</strong> 표시
            <br />* 따릉이 가용 확률은 도착 예정 시각 기준 추정값
          </div>
        )}
      </div>
    </div>
  );
}
