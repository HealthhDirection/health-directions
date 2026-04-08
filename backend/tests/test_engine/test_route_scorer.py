"""RouteScorer 단위 테스트 — mock 불필요 (순수 계산 로직)."""

import pytest
from app.engine.route_scorer import RouteScorer


def _route(type_="bus_only", duration=20.0, transfers=0, bike_prob=1.0, walk_dist=0.0, bike_dist=0.0):
    return {
        "type": type_,
        "tmap_duration_min": duration,
        "estimated_duration_min": duration,
        "transfers": transfers,
        "bike_probability": bike_prob,
        "walk_dist_m": walk_dist,
        "bike_dist_m": bike_dist,
        "intersections": [],
        "polyline": [],
    }


def test_empty_input():
    assert RouteScorer().score([]) == []


def test_single_route_score():
    """단일 경로: max_time==duration → speed_score=0, 나머지 1.0 → 합계 0.60.
    0.4*0 + 0.25*1 + 0.2*1 + 0.15*1 = 0.60
    """
    result = RouteScorer().score([_route(duration=15.0)])
    assert len(result) == 1
    assert result[0]["score"] == pytest.approx(0.60, abs=0.01)


def test_faster_route_ranked_first():
    routes = [_route(duration=30.0), _route(duration=10.0)]
    result = RouteScorer().score(routes)
    assert result[0]["estimated_duration_min"] == 10.0


def test_returns_at_most_3():
    routes = [_route(duration=10 + i) for i in range(5)]
    assert len(RouteScorer().score(routes)) == 3


def test_score_in_range():
    routes = [
        _route("bus_only",  20, transfers=0, bike_prob=1.0, walk_dist=500),
        _route("bus_bike",  25, transfers=1, bike_prob=0.7, walk_dist=300, bike_dist=800),
        _route("walk_bike", 18, transfers=0, bike_prob=0.9, walk_dist=100, bike_dist=1500),
    ]
    for r in RouteScorer().score(routes):
        assert 0.0 <= r["score"] <= 1.0


def test_score_fields_present():
    routes = [_route(duration=20.0)]
    result = RouteScorer().score(routes)
    r = result[0]
    assert "score" in r
    assert "speed_score" in r
    assert "reliability_score" in r
    assert "comfort_score" in r


def test_more_transfers_lower_reliability():
    low_transfer  = _route(duration=20, transfers=0)
    high_transfer = _route(duration=20, transfers=3)
    result = RouteScorer().score([low_transfer, high_transfer])
    scores = {r["transfers"]: r["reliability_score"] for r in result}
    assert scores[0] > scores[3]


def test_higher_bike_prob_ranks_better():
    high_prob = _route("bus_bike", duration=20, bike_prob=0.95)
    low_prob  = _route("bus_bike", duration=20, bike_prob=0.10)
    result = RouteScorer().score([high_prob, low_prob])
    assert result[0]["bike_probability"] == 0.95


def test_shorter_walk_better_comfort():
    short_walk = _route(walk_dist=200)
    long_walk  = _route(walk_dist=1800)
    result = RouteScorer().score([short_walk, long_walk])
    scores = {r["walk_dist_m"]: r["comfort_score"] for r in result}
    assert scores[200] > scores[1800]
