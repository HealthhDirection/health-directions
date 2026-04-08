"""이동 시간 추정기.

TMAP 베이스 시간 + 신호등 지연 보정.
"""

import json

from loguru import logger

# 신호 주기 기본값 (데이터 없을 때 사용)
_DEFAULT_CYCLE_SEC = 60.0


class TimeEstimator:
    # 도보 속도: 80m/min, 자전거 속도: 250m/min
    WALK_SPEED_M_PER_MIN = 80
    BIKE_SPEED_M_PER_MIN = 250
    BIKE_RENTAL_MIN = 1  # 따릉이 대여 소요시간 (고정)

    def __init__(self, redis_client):
        self.redis = redis_client

    def estimate(self, route: dict) -> float:
        """경로의 총 예상 소요시간(분)을 계산한다."""
        base = float(route.get("tmap_duration_min", 0.0))
        bike_dist_m = float(route.get("bike_dist_m", 0.0))
        intersections = route.get("intersections", [])

        # 1. 교차로별 신호 대기시간 합산
        signal_delay = sum(
            self.get_signal_delay(inter["intersection_id"])
            for inter in intersections
        )

        # 2. 자전거 구간 추가 시간 계산
        bike_bonus = 0.0
        rental_min = 0.0
        if bike_dist_m > 0:
            bike_bonus = bike_dist_m / self.BIKE_SPEED_M_PER_MIN
            rental_min = self.BIKE_RENTAL_MIN

        total = base + signal_delay + bike_bonus + rental_min
        return round(total, 2)

    # 8방향 접두사 (signal_collector.py와 동일)
    _DIRECTIONS = ["nt", "et", "st", "wt", "ne", "se", "sw", "nw"]

    def _extract_pedestrian_delay(self, item: dict) -> float:
        """raw item에서 보행 신호(Pd) 잔여시간(분)을 추출한다.

        첫 번째로 데이터가 존재하는 방향의 보행 신호를 사용한다.
        - "protected-Movement-Allowed" / "permissive-Movement-Allowed" → 0분 (GREEN)
        - "stop-And-Remain" → remaining_sec / 60분 (RED)
        - 그 외 또는 없음 → 기본값 0.5분
        잔여시간 단위: 데시초(1/10초) → ÷10 → 초 → ÷60 → 분
        """
        for prefix in self._DIRECTIONS:
            status = item.get(f"{prefix}PdsgSttsNm", "")
            remain_raw = item.get(f"{prefix}PdsgRmndCs", "")

            if not status and not remain_raw:
                continue

            status_lower = status.lower().strip()
            if status_lower in ("protected-movement-allowed", "permissive-movement-allowed"):
                return 0.0

            if status_lower == "stop-and-remain" and remain_raw:
                try:
                    remain_sec = int(float(remain_raw)) / 10.0
                    return remain_sec / 60.0
                except (ValueError, TypeError):
                    pass

            # YELLOW 또는 파싱 실패 → 기본값
            return _DEFAULT_CYCLE_SEC / 2 / 60

        return _DEFAULT_CYCLE_SEC / 2 / 60

    def get_signal_delay(self, intersection_id: str) -> float:
        """
        Redis signal:{intersection_id} 에서 보행 신호 잔여시간을 조회한다.
        - current_phase == "GREEN" → 0분
        - current_phase == "RED"   → remaining_sec / 60 분
        - 데이터 없음              → cycle_time / 2 / 60 (기본값 0.5분)
        """
        redis_key = f"signal:{intersection_id}"
        raw = self.redis.get(redis_key)

        if raw is None:
            logger.debug("신호등 Redis 데이터 없음: intersection_id={}", intersection_id)
            return _DEFAULT_CYCLE_SEC / 2 / 60  # 기본 0.5분

        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            logger.warning("신호등 Redis 값 파싱 실패: key={}", redis_key)
            return _DEFAULT_CYCLE_SEC / 2 / 60

        # Redis 값은 교차로 raw item dict (signal_collector.py 참고)
        # 8방향(nt/et/st/wt/ne/se/sw/nw) 보행 신호(Pd) 중 첫 번째 유효 데이터 사용
        if not isinstance(data, dict):
            return _DEFAULT_CYCLE_SEC / 2 / 60

        return self._extract_pedestrian_delay(data)
