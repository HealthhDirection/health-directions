"""따릉이 대여소 가용 데이터 수집기."""

from app.collectors.base import BaseCollector


class BikeCollector(BaseCollector):
    name = "bike"

    def collect(self) -> int:
        # TODO: Phase 1에서 구현
        # 1. 따릉이 실시간 대여정보 API 호출 (페이지네이션)
        # 2. 강서구 대여소만 필터링
        # 3. realtime.bike_availability에 저장
        # 4. Redis 캐시 업데이트 (bike:avail:{station_id}, bike:all_stations)
        raise NotImplementedError
