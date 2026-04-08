/**
 * 출발/도착 검색 바 + Kakao Places 자동완성.
 *
 * props:
 *   onSearch  ({ origin, destination }) => void
 *             origin/destination: { lat, lng, name }
 */

import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import useRouteStore from "../../store/routeStore";

function PlaceInput({ placeholder, icon, value, onChange, onSelect }) {
  const [query, setQuery] = useState(value?.name ?? "");
  const [suggestions, setSuggestions] = useState([]);
  const wrapRef = useRef(null);

  // 외부 클릭 시 드롭다운 닫기
  useEffect(() => {
    const handler = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) {
        setSuggestions([]);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleInput = (e) => {
    const q = e.target.value;
    setQuery(q);
    onChange(null); // 선택 초기화

    if (!q.trim() || !window.kakao?.maps?.services) {
      setSuggestions([]);
      return;
    }

    const ps = new window.kakao.maps.services.Places();
    ps.keywordSearch(q, (data, status) => {
      if (status === window.kakao.maps.services.Status.OK) {
        setSuggestions(data.slice(0, 5));
      } else {
        setSuggestions([]);
      }
    });
  };

  const handleSelect = (place) => {
    setQuery(place.place_name);
    setSuggestions([]);
    onSelect({
      lat: parseFloat(place.y),
      lng: parseFloat(place.x),
      name: place.place_name,
    });
  };

  return (
    <div className="search-input-wrap" ref={wrapRef}>
      <input
        className="search-input"
        placeholder={placeholder}
        value={query}
        onChange={handleInput}
      />
      <span className="search-input-icon">{icon}</span>
      {suggestions.length > 0 && (
        <div className="search-suggestions">
          {suggestions.map((s) => (
            <div
              key={s.id}
              className="search-suggestion-item"
              onMouseDown={() => handleSelect(s)}
            >
              <strong>{s.place_name}</strong>
              <br />
              <span style={{ color: "#6b7280", fontSize: 11 }}>{s.road_address_name || s.address_name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function SearchBar() {
  const navigate = useNavigate();
  const { origin, destination, setOrigin, setDestination, setLoading } = useRouteStore();

  const handleSearch = () => {
    if (!origin || !destination) {
      alert("출발지와 도착지를 모두 입력하세요.");
      return;
    }
    setLoading(true);
    navigate(`/routes?olat=${origin.lat}&olng=${origin.lng}&dlat=${destination.lat}&dlng=${destination.lng}`);
  };

  return (
    <div className="search-bar">
      <PlaceInput
        placeholder="출발지를 입력하세요"
        icon="📍"
        value={origin}
        onChange={setOrigin}
        onSelect={setOrigin}
      />
      <PlaceInput
        placeholder="도착지를 입력하세요"
        icon="🏁"
        value={destination}
        onChange={setDestination}
        onSelect={setDestination}
      />
      <button
        className="btn btn-primary"
        onClick={handleSearch}
        disabled={!origin || !destination}
        style={{ width: "100%" }}
      >
        경로 검색
      </button>
    </div>
  );
}
