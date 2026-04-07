"""교통 신호등 상태 수집기."""

from app.collectors.base import BaseCollector


class SignalCollector(BaseCollector):
    name = "signal"

    def collect(self) -> int:
        # TODO: Phase 1에서 구현
        # 1. 강서구 주요 교차로 목록 조회 (master.intersections)
        # 2. 각 교차로별 신호 상태 API 호출
        # 3. realtime.signal_state에 저장
        # 4. Redis 캐시 업데이트 (signal:{intersection_id})
        raise NotImplementedError
