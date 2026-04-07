"""따릉이 가용성 예측기.

Phase 1: 규칙 기반 (시간대별 소모율)
Phase 2: ML 기반 (LightGBM/GBR, 2~4주 데이터 축적 후)
"""

from datetime import datetime, timedelta


class BikePredictor:
    def __init__(self, redis_client):
        self.redis = redis_client

    def predict_availability(
        self, station_id: str, minutes_ahead: int
    ) -> float:
        """도착 시점의 자전거 대여 가능 확률(0.0~1.0)을 반환한다."""
        # TODO: Phase 3에서 구현
        # 규칙 기반:
        # 1. Redis에서 현재 수량 조회
        # 2. 시간대별 소모율 적용
        # 3. 예측 수량 → 확률 변환
        #    3대 이상 → 0.95
        #    1대 이상 → 0.70
        #    0대 → max(0.1, 현재비율)
        raise NotImplementedError
