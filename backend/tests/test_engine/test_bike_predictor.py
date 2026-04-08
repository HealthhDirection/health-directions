"""BikePredictor 단위 테스트 — Redis mock 사용."""

import json
from unittest.mock import MagicMock

import pytest
from app.engine.bike_predictor import BikePredictor


def _redis(value=None):
    r = MagicMock()
    r.get.return_value = value
    return r


# ── 데이터 없음 ──────────────────────────────────────────────────────────────

def test_no_redis_data_returns_50pct():
    pred = BikePredictor(_redis(None))
    assert pred.predict_availability("ST-001", 10) == 0.5


def test_invalid_redis_value_returns_50pct():
    pred = BikePredictor(_redis("not-a-number"))
    assert pred.predict_availability("ST-001", 10) == 0.5


# ── 현재 시점 (minutes_ahead=0) ───────────────────────────────────────────────

def test_many_bikes_high_probability():
    """10대 → 3대 이상 기준 → 95%."""
    pred = BikePredictor(_redis("10"))
    assert pred.predict_availability("ST-001", 0) == 0.95


def test_two_bikes_medium_probability():
    """2대 → 1대 이상 기준 → 70%."""
    pred = BikePredictor(_redis("2"))
    assert pred.predict_availability("ST-001", 0) == 0.70


def test_zero_bikes_low_probability():
    """0대 → 10%."""
    pred = BikePredictor(_redis("0"))
    assert pred.predict_availability("ST-001", 0) == 0.10


def test_exactly_three_bikes():
    pred = BikePredictor(_redis("3"))
    assert pred.predict_availability("ST-001", 0) == 0.95


def test_exactly_one_bike():
    pred = BikePredictor(_redis("1"))
    assert pred.predict_availability("ST-001", 0) == 0.70


# ── 시간 경과 후 소모 ─────────────────────────────────────────────────────────

def test_depletion_reduces_probability(monkeypatch):
    """출퇴근 시간대(피크)에 60분 후 예측 수량 감소."""
    import app.engine.bike_predictor as mod
    from datetime import datetime

    # 피크 시간으로 강제 설정 (7시)
    monkeypatch.setattr(
        "app.engine.bike_predictor.datetime",
        type("MockDatetime", (), {"now": staticmethod(lambda: datetime(2024, 1, 1, 8, 0))})(),
    )

    pred = BikePredictor(_redis("5"))
    # 피크 소모율 20%/h → 60분 후 predicted = 5 * (1 - 0.20) = 4.0 → 95%
    assert pred.predict_availability("ST-001", 60) == 0.95


def test_heavy_depletion_drops_probability(monkeypatch):
    """피크 시간대 장시간 후 수량이 0에 가까워지면 확률 감소."""
    import app.engine.bike_predictor as mod
    from datetime import datetime

    monkeypatch.setattr(
        "app.engine.bike_predictor.datetime",
        type("MockDatetime", (), {"now": staticmethod(lambda: datetime(2024, 1, 1, 8, 0))})(),
    )

    # 3대, 피크 20%/h → 300분 후 predicted = 3 * (1 - 0.20*5) = 0 → 10%
    pred = BikePredictor(_redis("3"))
    assert pred.predict_availability("ST-001", 300) == 0.10


# ── 반환값 범위 ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("bikes,minutes", [
    ("0", 0), ("1", 10), ("5", 30), ("20", 60), ("0", 120),
])
def test_probability_always_valid_range(bikes, minutes):
    pred = BikePredictor(_redis(bikes))
    result = pred.predict_availability("ST-001", minutes)
    assert result in (0.10, 0.50, 0.70, 0.95)
