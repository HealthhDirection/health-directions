"""테스트 공통 픽스처."""

import pytest


@pytest.fixture
def sample_bus_arrival():
    """버스 도착 API 샘플 응답."""
    return {
        "stop_id": "22001",
        "route_id": "6631",
        "arrival_sec_1": 180,
        "arrival_sec_2": 540,
    }


@pytest.fixture
def sample_bike_availability():
    """따릉이 가용 API 샘플 응답."""
    return {
        "station_id": "ST-1001",
        "station_name": "발산역 1번출구",
        "available_bikes": 7,
        "available_racks": 13,
        "rack_count": 20,
    }
