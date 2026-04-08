"""따릉이 가용성 예측기.

Phase 1: 규칙 기반 (시간대별 소모율)
Phase 2: ML 기반 (LightGBM/GBR, 2~4주 데이터 축적 후)
"""

from datetime import datetime

from loguru import logger

# 시간대별 시간당 소모율 (대수 기준)
_PEAK_HOURS = frozenset(range(7, 10)) | frozenset(range(17, 20))  # 7~9시, 17~19시
_DAY_HOURS = frozenset(range(10, 17))  # 10~16시
_DEPLETION_RATE_PEAK = 0.20   # 출퇴근: 시간당 20% 소모
_DEPLETION_RATE_DAY = 0.10    # 낮: 시간당 10% 소모
_DEPLETION_RATE_OTHER = 0.05  # 기타: 시간당 5% 소모


class BikePredictor:
    def __init__(self, redis_client):
        self.redis = redis_client

    def predict_availability(
        self, station_id: str, minutes_ahead: int
    ) -> float:
        """도착 시점의 자전거 대여 가능 확률(0.0~1.0)을 반환한다."""
        # 1. Redis에서 현재 수량 조회
        redis_key = f"bike:avail:{station_id}"
        raw = self.redis.get(redis_key)

        if raw is None:
            logger.debug("따릉이 Redis 데이터 없음: station_id={}", station_id)
            return 0.5  # 데이터 없으면 불확실

        try:
            current_count = float(raw)
        except (ValueError, TypeError):
            logger.warning("따릉이 Redis 값 파싱 실패: key={}, value={}", redis_key, raw)
            return 0.5

        # 2. 시간대별 소모율 결정
        now_hour = datetime.now().hour
        if now_hour in _PEAK_HOURS:
            hourly_rate = _DEPLETION_RATE_PEAK
        elif now_hour in _DAY_HOURS:
            hourly_rate = _DEPLETION_RATE_DAY
        else:
            hourly_rate = _DEPLETION_RATE_OTHER

        # 3. 예측 수량 계산 (소수점 허용)
        hours_ahead = minutes_ahead / 60.0
        predicted_count = current_count * (1 - hourly_rate * hours_ahead)
        predicted_count = max(0.0, predicted_count)

        # 4. 예측 수량 → 확률 변환
        if predicted_count >= 3:
            return 0.95
        elif predicted_count >= 1:
            return 0.70
        else:
            return 0.10
