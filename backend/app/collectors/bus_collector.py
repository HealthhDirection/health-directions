"""버스 도착/위치 데이터 수집기."""

from app.collectors.base import BaseCollector


class BusCollector(BaseCollector):
    name = "bus"

    def collect(self) -> int:
        # TODO: Phase 1에서 구현
        # 1. 강서구 정류장 목록 조회 (master.bus_stops)
        # 2. 각 정류장별 버스 도착 정보 API 호출
        # 3. realtime.bus_arrivals에 저장
        # 4. Redis 캐시 업데이트
        raise NotImplementedError
