"""정류장/대여소 조회 API."""

from fastapi import APIRouter

router = APIRouter(tags=["stations"])


@router.get("/stations/bike")
def get_bike_stations():
    """강서구 따릉이 대여소 목록 + 실시간 가용 수량."""
    # TODO: Phase 1에서 구현
    # Redis bike:all_stations 캐시 조회
    return {"stations": []}


@router.get("/stations/bus")
def get_bus_stops():
    """강서구 버스 정류장 목록."""
    # TODO: Phase 1에서 구현
    # master.bus_stops 조회
    return {"stops": []}
