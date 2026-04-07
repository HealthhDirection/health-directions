"""경로 다기준 점수화.

가중치: 속도(0.4) + 안정성(0.25) + 자전거확률(0.2) + 편의성(0.15)
"""


class RouteScorer:
    WEIGHT_SPEED = 0.4
    WEIGHT_RELIABILITY = 0.25
    WEIGHT_BIKE_PROB = 0.2
    WEIGHT_COMFORT = 0.15

    def score(self, routes: list[dict]) -> list[dict]:
        """경로 목록에 점수를 매기고 상위 3개를 반환한다."""
        # TODO: Phase 2에서 구현
        # 각 경로별:
        #   speed_score = 1 - (travel_time / max_travel_time)
        #   reliability_score = 실시간 ETA 반영, 환승 패널티
        #   bike_probability = BikePredictor 결과 (버스만이면 1.0)
        #   comfort_score = 1 - (transfers * 0.3 + walk_dist / 2000)
        #   total = w_speed * speed + w_rel * rel + w_bike * bike + w_comfort * comfort
        raise NotImplementedError
