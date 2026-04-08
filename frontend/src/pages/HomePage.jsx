/**
 * 홈 페이지 — 지도 + 검색 UI
 * 강서구 중심 (lat: 37.5509, lng: 126.8495)
 */

import { useEffect, useState } from "react";
import KakaoMap from "../components/Map/KakaoMap";
import SearchBar from "../components/Search/SearchBar";
import { toBikeMarkers, toBusMarkers } from "../components/Map/StationMarker";
import api from "../utils/api";

export default function HomePage() {
  const [bikeMarkers, setBikeMarkers] = useState([]);
  const [busMarkers, setBusMarkers]   = useState([]);
  const [showBike, setShowBike]       = useState(true);
  const [showBus, setShowBus]         = useState(false);

  // 따릉이 대여소 로드
  useEffect(() => {
    if (!showBike) { setBikeMarkers([]); return; }
    api.get("/stations/bike")
      .then((res) => setBikeMarkers(toBikeMarkers(res.data.stations ?? [])))
      .catch(() => {});
  }, [showBike]);

  // 버스 정류장 로드
  useEffect(() => {
    if (!showBus) { setBusMarkers([]); return; }
    api.get("/stations/bus")
      .then((res) => setBusMarkers(toBusMarkers(res.data.stops ?? [])))
      .catch(() => {});
  }, [showBus]);

  const allMarkers = [...bikeMarkers, ...busMarkers];

  return (
    <div className="home-page">
      {/* 지도 영역 */}
      <div className="home-map-area">
        <KakaoMap markers={allMarkers} />
      </div>

      {/* 검색 패널 */}
      <div className="home-search-panel">
        <h1 style={{ fontSize: 18, fontWeight: 700, color: "#111827" }}>
          건강길찾기
        </h1>
        <p style={{ fontSize: 12, color: "#6b7280", marginTop: -4 }}>
          강서구 버스·따릉이 최적 경로
        </p>

        <SearchBar />

        {/* 레이어 토글 */}
        <div style={{ display: "flex", gap: 8 }}>
          <button
            className={`btn ${showBike ? "btn-primary" : "btn-secondary"}`}
            style={{ flex: 1, fontSize: 12 }}
            onClick={() => setShowBike((v) => !v)}
          >
            🚲 따릉이
          </button>
          <button
            className={`btn ${showBus ? "btn-primary" : "btn-secondary"}`}
            style={{ flex: 1, fontSize: 12 }}
            onClick={() => setShowBus((v) => !v)}
          >
            🚌 버스정류장
          </button>
        </div>

        {/* 범례 */}
        {showBike && (
          <div style={{ display: "flex", gap: 10, fontSize: 11, color: "#6b7280" }}>
            <span style={{ color: "#16a34a" }}>● 3대+</span>
            <span style={{ color: "#d97706" }}>● 1~2대</span>
            <span style={{ color: "#dc2626" }}>● 0대</span>
          </div>
        )}
      </div>
    </div>
  );
}
