"""API 통합 테스트 — FastAPI TestClient 사용 (DB/Redis mock)."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── 헬스체크 ─────────────────────────────────────────────────────────────────

def test_health_check():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_config_check():
    resp = client.get("/config/check")
    assert resp.status_code == 200
    data = resp.json()
    assert "SIGNAL_API_KEY" in data
    assert "TMAP_APP_KEY" in data


# ── /api/stations/bike ────────────────────────────────────────────────────────

def _mock_redis_no_cache():
    r = MagicMock()
    r.get.return_value = None
    return r


def _mock_pg_bike_stations():
    conn = MagicMock()
    cursor = MagicMock()
    cursor.__enter__ = lambda s: cursor
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchall.return_value = [
        ("ST-1001", "발산역 1번출구", 37.5580, 126.8380, 5, 20),
        ("ST-1002", "화곡역 2번출구", 37.5499, 126.8490, 0, 15),
    ]
    conn.cursor.return_value = cursor
    return conn


@patch("app.api.stations.get_redis", return_value=_mock_redis_no_cache())
@patch("app.api.stations.get_pg_connection", return_value=_mock_pg_bike_stations())
def test_get_bike_stations(mock_pg, mock_redis):
    resp = client.get("/api/stations/bike")
    assert resp.status_code == 200
    data = resp.json()
    assert "stations" in data
    assert len(data["stations"]) == 2
    assert data["stations"][0]["station_id"] == "ST-1001"
    assert data["stations"][0]["available_bikes"] == 5


@patch("app.api.stations.get_redis")
def test_get_bike_stations_from_cache(mock_get_redis):
    import json
    cached_stations = [
        {"station_id": "ST-9999", "station_name": "캐시역", "lat": 37.55, "lng": 126.84,
         "available_bikes": 3, "rack_count": 10}
    ]
    redis_mock = MagicMock()
    redis_mock.get.return_value = json.dumps(cached_stations).encode()
    mock_get_redis.return_value = redis_mock

    resp = client.get("/api/stations/bike")
    assert resp.status_code == 200
    data = resp.json()
    assert data["stations"][0]["station_id"] == "ST-9999"


# ── /api/stations/bus ────────────────────────────────────────────────────────

def _mock_pg_bus_stops():
    conn = MagicMock()
    cursor = MagicMock()
    cursor.__enter__ = lambda s: cursor
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchall.return_value = [
        ("22001", "발산역", 37.5580, 126.8380),
        ("22002", "화곡역", 37.5499, 126.8490),
    ]
    conn.cursor.return_value = cursor
    return conn


@patch("app.api.stations.get_pg_connection", return_value=_mock_pg_bus_stops())
def test_get_bus_stops(mock_pg):
    resp = client.get("/api/stations/bus")
    assert resp.status_code == 200
    data = resp.json()
    assert "stops" in data
    assert len(data["stops"]) == 2
    assert data["stops"][0]["stop_id"] == "22001"
    assert data["stops"][0]["lat"] == pytest.approx(37.5580)


@patch("app.api.stations.get_pg_connection", side_effect=Exception("DB down"))
def test_get_bus_stops_db_error(mock_pg):
    resp = client.get("/api/stations/bus")
    assert resp.status_code == 500


# ── /api/routes ───────────────────────────────────────────────────────────────

def _mock_pg_empty():
    """빈 결과를 반환하는 PG 커넥션 mock."""
    conn = MagicMock()
    cursor = MagicMock()
    cursor.__enter__ = lambda s: cursor
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchall.return_value = []
    conn.cursor.return_value = cursor
    return conn


def _mock_redis_empty():
    r = MagicMock()
    r.get.return_value = None
    r.mget.return_value = [None] * 9
    return r


@patch("app.api.routes.get_pg_connection", return_value=_mock_pg_empty())
@patch("app.api.routes.get_redis", return_value=_mock_redis_empty())
@patch("app.engine.route_finder.RouteFinder._fetch_tmap_route", return_value=None)
def test_get_routes_no_result(mock_tmap, mock_redis, mock_pg):
    resp = client.get(
        "/api/routes",
        params={"origin_lat": 37.556, "origin_lng": 126.838, "dest_lat": 37.545, "dest_lng": 126.850},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "routes" in data


@patch("app.api.routes.get_pg_connection", side_effect=Exception("DB down"))
@patch("app.api.routes.get_redis", side_effect=Exception("Redis down"))
def test_get_routes_db_error(mock_redis, mock_pg):
    resp = client.get(
        "/api/routes",
        params={"origin_lat": 37.556, "origin_lng": 126.838, "dest_lat": 37.545, "dest_lng": 126.850},
    )
    assert resp.status_code == 503


def test_get_routes_missing_params():
    resp = client.get("/api/routes", params={"origin_lat": 37.556})
    assert resp.status_code == 422


# ── /api/status ───────────────────────────────────────────────────────────────

@patch("app.api.status.get_pg_connection", return_value=_mock_pg_empty())
def test_get_status(mock_pg):
    resp = client.get("/api/status")
    assert resp.status_code == 200
