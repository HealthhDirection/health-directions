/**
 * 따릉이 가용 확률 게이지.
 *
 * props:
 *   probability  number 0~1
 *   stationName  string (선택)
 *   ahead        number — 몇 분 후 기준 (선택)
 */

export default function BikeAvailability({ probability = 1, stationName, ahead }) {
  const pct = Math.round(probability * 100);

  let cls, emoji;
  if (pct >= 80)      { cls = "high"; emoji = "🟢"; }
  else if (pct >= 40) { cls = "mid";  emoji = "🟡"; }
  else                { cls = "low";  emoji = "🔴"; }

  const fillColor = cls === "high" ? "#16a34a" : cls === "mid" ? "#d97706" : "#dc2626";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      {stationName && (
        <span style={{ fontSize: 11, color: "#6b7280" }}>
          {stationName}{ahead != null ? ` · ${ahead}분 후` : ""}
        </span>
      )}
      <div className={`bike-availability ${cls}`}>
        <span>{emoji} 따릉이 {pct}%</span>
        <div className="bike-prob-bar" style={{ width: 60 }}>
          <div
            className="bike-prob-fill"
            style={{ width: `${pct}%`, background: fillColor }}
          />
        </div>
      </div>
    </div>
  );
}
