/**
 * Kakao Maps 래퍼 컴포넌트.
 * VITE_KAKAO_MAP_KEY 환경변수로 SDK를 동적 로드.
 *
 * props:
 *   center       { lat, lng }       — 지도 중심 (기본: 강서구)
 *   zoom         number             — 줌 레벨 (기본: 14)
 *   markers      Array<{ lat, lng, label?, color? }>
 *   polylines    Array<{ path: [{lat,lng}], color?, width?, opacity? }>
 *   onMapClick   (latLng) => void
 */

import { useEffect, useRef } from "react";

const GANGSEO_CENTER = { lat: 37.5509, lng: 126.8495 };
const DEFAULT_ZOOM = 14;

export default function KakaoMap({
  center = GANGSEO_CENTER,
  zoom = DEFAULT_ZOOM,
  markers = [],
  polylines = [],
  onMapClick,
}) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef([]);
  const polylinesRef = useRef([]);

  // SDK 로드 및 지도 초기화
  useEffect(() => {
    const apiKey = import.meta.env.VITE_KAKAO_MAP_KEY;
    if (!apiKey) {
      console.warn("[KakaoMap] VITE_KAKAO_MAP_KEY 환경변수가 없습니다. .env 파일을 확인하세요.");
      return;
    }

    const initMap = () => {
      console.log("[KakaoMap] initMap 호출됨, window.kakao:", !!window.kakao);
      window.kakao.maps.load(() => {
        console.log("[KakaoMap] kakao.maps.load 콜백 실행, container:", containerRef.current);
        const mapOptions = {
          center: new window.kakao.maps.LatLng(center.lat, center.lng),
          level: zoom,
        };
        mapRef.current = new window.kakao.maps.Map(containerRef.current, mapOptions);
        console.log("[KakaoMap] 지도 생성 완료");

        if (onMapClick) {
          window.kakao.maps.event.addListener(mapRef.current, "click", (mouseEvent) => {
            const latlng = mouseEvent.latLng;
            onMapClick({ lat: latlng.getLat(), lng: latlng.getLng() });
          });
        }
      });
    };

    if (window.kakao?.maps) {
      initMap();
    } else {
      const existing = document.querySelector(`script[data-kakao-maps]`);
      if (existing) {
        existing.addEventListener("load", initMap);
        return;
      }
      const script = document.createElement("script");
      script.setAttribute("data-kakao-maps", "1");
      script.src = `//dapi.kakao.com/v2/maps/sdk.js?appkey=${apiKey}&libraries=services&autoload=false`;
      script.onload = () => { console.log("[KakaoMap] SDK 스크립트 로드됨"); initMap(); };
      script.onerror = (e) => console.error("[KakaoMap] SDK 스크립트 로드 실패", e);
      document.head.appendChild(script);
      console.log("[KakaoMap] 스크립트 추가됨, src:", script.src);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 마커 동기화
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !window.kakao?.maps) return;

    markersRef.current.forEach((m) => m.setMap(null));
    markersRef.current = [];

    markers.forEach(({ lat, lng, label, color = "#2563eb" }) => {
      const position = new window.kakao.maps.LatLng(lat, lng);

      if (label) {
        const overlay = new window.kakao.maps.CustomOverlay({
          position,
          content: `<div style="background:${color};color:#fff;padding:3px 8px;border-radius:12px;font-size:11px;font-weight:600;white-space:nowrap;box-shadow:0 1px 4px rgba(0,0,0,.3)">${label}</div>`,
          yAnchor: 1.8,
          zIndex: 10,
        });
        overlay.setMap(map);
        markersRef.current.push(overlay);
      } else {
        const marker = new window.kakao.maps.Marker({ position, map });
        markersRef.current.push(marker);
      }
    });
  }, [markers]);

  // 폴리라인 동기화
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !window.kakao?.maps) return;

    polylinesRef.current.forEach((p) => p.setMap(null));
    polylinesRef.current = [];

    polylines.forEach(({ path, color = "#2563eb", width = 5, opacity = 0.8 }) => {
      const linePath = path.map((pt) => new window.kakao.maps.LatLng(pt.lat, pt.lng));
      const polyline = new window.kakao.maps.Polyline({
        map,
        path: linePath,
        strokeWeight: width,
        strokeColor: color,
        strokeOpacity: opacity,
        strokeStyle: "solid",
      });
      polylinesRef.current.push(polyline);
    });
  }, [polylines]);

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "100%", background: "#e5e7eb" }}
    />
  );
}
