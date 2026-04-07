"""이동 시간 추정기.

TMAP 베이스 시간 + 신호등 지연 보정.
"""


class TimeEstimator:
    # 도보 속도: 80m/min, 자전거 속도: 250m/min
    WALK_SPEED_M_PER_MIN = 80
    BIKE_SPEED_M_PER_MIN = 250
    BIKE_RENTAL_MIN = 1  # 따릉이 대여 소요시간 (고정)

    def __init__(self, redis_client):
        self.redis = redis_client

    def estimate(self, route: dict) -> float:
        """경로의 총 예상 소요시간(분)을 계산한다."""
        # TODO: Phase 2에서 구현
        # total = walk_to_stop + bus_wait + bus_travel
        #       + walk_to_bike_station + signal_delay
        #       + bike_rental + cycling
        raise NotImplementedError

    def get_signal_delay(self, lat: float, lng: float) -> float:
        """해당 좌표 근처 교차로의 예상 신호 대기시간(분)."""
        # TODO: Phase 2에서 구현
        # 1. 50m 이내 교차로 검색
        # 2. Redis에서 보행 신호 잔여시간 조회
        # 3. GREEN이면 0, RED이면 remaining_sec 반환
        # 4. 데이터 없으면 cycle_time / 2 (통계 평균)
        return 0.0
