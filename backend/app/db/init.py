"""DB 스키마 초기화. 최초 1회 실행."""

from app.db.connection import get_pg_connection

SCHEMAS = ["master", "realtime", "history"]

MASTER_TABLES = """
-- 버스 정류장
CREATE TABLE IF NOT EXISTS master.bus_stops (
    stop_id       TEXT PRIMARY KEY,
    stop_name     TEXT NOT NULL,
    latitude      DOUBLE PRECISION NOT NULL,
    longitude     DOUBLE PRECISION NOT NULL,
    district      TEXT DEFAULT '강서구',
    route_ids     TEXT[],
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);

-- 버스 노선
CREATE TABLE IF NOT EXISTS master.bus_routes (
    route_id      TEXT PRIMARY KEY,
    route_name    TEXT NOT NULL,
    route_type    TEXT,
    stop_sequence JSONB,
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- 따릉이 대여소
CREATE TABLE IF NOT EXISTS master.bike_stations (
    station_id    TEXT PRIMARY KEY,
    station_name  TEXT NOT NULL,
    latitude      DOUBLE PRECISION NOT NULL,
    longitude     DOUBLE PRECISION NOT NULL,
    rack_count    INT,
    district      TEXT DEFAULT '강서구',
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- 교통 신호 교차로
-- longitude: RTI API가 경도 미제공, TMAP geocoding으로 보완 시 채워짐
CREATE TABLE IF NOT EXISTS master.intersections (
    intersection_id TEXT PRIMARY KEY,
    intersection_name TEXT,
    latitude      DOUBLE PRECISION NOT NULL,
    longitude     DOUBLE PRECISION,
    direction_count INT,
    signal_meta   JSONB,
    created_at    TIMESTAMPTZ DEFAULT now()
);
"""

REALTIME_TABLES = """
CREATE TABLE IF NOT EXISTS realtime.bus_arrivals (
    id            BIGSERIAL PRIMARY KEY,
    stop_id       TEXT NOT NULL,
    route_id      TEXT NOT NULL,
    arrival_sec_1 INT,
    arrival_sec_2 INT,
    bus_id_1      TEXT,
    bus_id_2      TEXT,
    congestion_1  INT,
    collected_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS realtime.bus_positions (
    id            BIGSERIAL PRIMARY KEY,
    route_id      TEXT NOT NULL,
    bus_id        TEXT NOT NULL,
    latitude      DOUBLE PRECISION,
    longitude     DOUBLE PRECISION,
    stop_id       TEXT,
    congestion    INT,
    collected_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS realtime.bike_availability (
    id            BIGSERIAL PRIMARY KEY,
    station_id    TEXT NOT NULL,
    available_bikes INT NOT NULL,
    available_racks INT NOT NULL,
    collected_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS realtime.signal_state (
    id            BIGSERIAL PRIMARY KEY,
    intersection_id TEXT NOT NULL,
    direction     TEXT NOT NULL,
    current_phase TEXT NOT NULL,
    remaining_sec INT,
    cycle_sec     INT,
    collected_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

HISTORY_TABLES = """
CREATE TABLE IF NOT EXISTS history.bike_hourly (
    station_id    TEXT NOT NULL,
    hour_ts       TIMESTAMPTZ NOT NULL,
    avg_bikes     DOUBLE PRECISION,
    min_bikes     INT,
    max_bikes     INT,
    sample_count  INT,
    PRIMARY KEY (station_id, hour_ts)
);

CREATE TABLE IF NOT EXISTS history.route_requests (
    id            BIGSERIAL PRIMARY KEY,
    origin_lat    DOUBLE PRECISION,
    origin_lng    DOUBLE PRECISION,
    dest_lat      DOUBLE PRECISION,
    dest_lng      DOUBLE PRECISION,
    recommended_routes JSONB,
    selected_route_idx INT,
    request_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS history.collector_log (
    id            BIGSERIAL PRIMARY KEY,
    collector     TEXT NOT NULL,
    status        TEXT NOT NULL,
    records_count INT,
    error_msg     TEXT,
    duration_ms   INT,
    collected_at  TIMESTAMPTZ DEFAULT now()
);
"""

INDEXES = """
CREATE INDEX IF NOT EXISTS idx_bus_stops_geo ON master.bus_stops (latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_bike_stations_geo ON master.bike_stations (latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_intersections_geo ON master.intersections (latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_bus_arr_stop ON realtime.bus_arrivals (stop_id, collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_bus_pos_route ON realtime.bus_positions (route_id, collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_bike_avail ON realtime.bike_availability (station_id, collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_signal_state ON realtime.signal_state (intersection_id, collected_at DESC);
"""


def init_db():
    """모든 스키마와 테이블을 생성한다."""
    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            for schema in SCHEMAS:
                cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
            cur.execute(MASTER_TABLES)
            cur.execute(REALTIME_TABLES)
            cur.execute(HISTORY_TABLES)
            cur.execute(INDEXES)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print("DB 초기화 완료")
