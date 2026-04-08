"""TimeEstimator 단위 테스트 — Redis mock 사용."""

import json
from unittest.mock import MagicMock

import pytest
from app.engine.time_estimator import TimeEstimator

_DEFAULT_DELAY = 60.0 / 2 / 60  # 0.5분 (기본값)


def _redis(value=None):
    r = MagicMock()
    r.get.return_value = value
    return r


# ── get_signal_delay ──────────────────────────────────────────────────────────

def test_signal_delay_no_data():
    est = TimeEstimator(_redis(None))
    assert est.get_signal_delay("999") == pytest.approx(_DEFAULT_DELAY, abs=0.001)


def test_signal_delay_invalid_json():
    est = TimeEstimator(_redis("invalid-json"))
    assert est.get_signal_delay("999") == pytest.approx(_DEFAULT_DELAY, abs=0.001)


def test_signal_delay_green():
    """GREEN 신호 → 지연 0분."""
    item = {"ntPdsgSttsNm": "protected-Movement-Allowed", "ntPdsgRmndCs": ""}
    est = TimeEstimator(_redis(json.dumps(item)))
    assert est.get_signal_delay("101") == pytest.approx(0.0, abs=0.001)


def test_signal_delay_green_permissive():
    item = {"ntPdsgSttsNm": "permissive-Movement-Allowed", "ntPdsgRmndCs": "600"}
    est = TimeEstimator(_redis(json.dumps(item)))
    assert est.get_signal_delay("101") == pytest.approx(0.0, abs=0.001)


def test_signal_delay_red():
    """RED 신호 → 잔여시간 30초(300 데시초) → 0.5분."""
    item = {"ntPdsgSttsNm": "stop-And-Remain", "ntPdsgRmndCs": "300"}
    est = TimeEstimator(_redis(json.dumps(item)))
    expected = 30.0 / 60.0
    assert est.get_signal_delay("101") == pytest.approx(expected, abs=0.001)


def test_signal_delay_red_60sec():
    """RED 신호 → 600 데시초 = 60초 → 1분."""
    item = {"ntPdsgSttsNm": "stop-And-Remain", "ntPdsgRmndCs": "600"}
    est = TimeEstimator(_redis(json.dumps(item)))
    assert est.get_signal_delay("101") == pytest.approx(1.0, abs=0.001)


def test_signal_delay_yellow_default():
    """YELLOW(clearance) → 기본값 0.5분."""
    item = {"ntPdsgSttsNm": "protected-clearance", "ntPdsgRmndCs": "200"}
    est = TimeEstimator(_redis(json.dumps(item)))
    assert est.get_signal_delay("101") == pytest.approx(_DEFAULT_DELAY, abs=0.001)


def test_signal_delay_fallback_east_direction():
    """nt 방향 데이터 없고 et 방향 GREEN → 0분."""
    item = {"etPdsgSttsNm": "protected-Movement-Allowed", "etPdsgRmndCs": ""}
    est = TimeEstimator(_redis(json.dumps(item)))
    assert est.get_signal_delay("101") == pytest.approx(0.0, abs=0.001)


def test_signal_delay_all_empty_directions():
    """모든 방향 데이터 없음 → 기본값."""
    est = TimeEstimator(_redis(json.dumps({})))
    assert est.get_signal_delay("101") == pytest.approx(_DEFAULT_DELAY, abs=0.001)


# ── estimate ─────────────────────────────────────────────────────────────────

def test_estimate_bus_only_no_signal():
    est = TimeEstimator(_redis(None))
    route = {"tmap_duration_min": 20.0, "bike_dist_m": 0.0, "intersections": []}
    assert est.estimate(route) == pytest.approx(20.0, abs=0.01)


def test_estimate_with_signal_red():
    """버스 경로 + RED 신호 30초 → 20분 + 0.5분 = 20.5분."""
    item = {"ntPdsgSttsNm": "stop-And-Remain", "ntPdsgRmndCs": "300"}
    est = TimeEstimator(_redis(json.dumps(item)))
    route = {
        "tmap_duration_min": 20.0,
        "bike_dist_m": 0.0,
        "intersections": [{"intersection_id": "101"}],
    }
    assert est.estimate(route) == pytest.approx(20.5, abs=0.01)


def test_estimate_with_signal_green():
    """GREEN 신호 → 지연 없음."""
    item = {"ntPdsgSttsNm": "protected-Movement-Allowed", "ntPdsgRmndCs": ""}
    est = TimeEstimator(_redis(json.dumps(item)))
    route = {
        "tmap_duration_min": 15.0,
        "bike_dist_m": 0.0,
        "intersections": [{"intersection_id": "202"}],
    }
    assert est.estimate(route) == pytest.approx(15.0, abs=0.01)


def test_estimate_bus_bike():
    """버스+자전거: 20분(버스) + 500m/250mpm(자전거 2분) + 1분(대여) = 23분."""
    est = TimeEstimator(_redis(None))
    route = {
        "tmap_duration_min": 20.0,
        "bike_dist_m": 500.0,
        "intersections": [],
    }
    assert est.estimate(route) == pytest.approx(23.0, abs=0.01)


def test_estimate_multiple_intersections():
    """교차로 2개 × RED 30초 → 20분 + 1분 = 21분."""
    item = {"ntPdsgSttsNm": "stop-And-Remain", "ntPdsgRmndCs": "300"}
    redis_mock = MagicMock()
    redis_mock.get.return_value = json.dumps(item)
    est = TimeEstimator(redis_mock)
    route = {
        "tmap_duration_min": 20.0,
        "bike_dist_m": 0.0,
        "intersections": [{"intersection_id": "101"}, {"intersection_id": "102"}],
    }
    assert est.estimate(route) == pytest.approx(21.0, abs=0.01)


def test_estimate_result_is_rounded():
    est = TimeEstimator(_redis(None))
    route = {"tmap_duration_min": 17.333, "bike_dist_m": 0.0, "intersections": []}
    result = est.estimate(route)
    # 소수점 2자리로 반올림
    assert result == round(result, 2)
