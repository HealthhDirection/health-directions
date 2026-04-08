"""경로 다기준 점수화.

가중치: 속도(0.4) + 안정성(0.25) + 자전거확률(0.2) + 편의성(0.15)
"""

from loguru import logger


class RouteScorer:
    WEIGHT_SPEED = 0.4
    WEIGHT_RELIABILITY = 0.25
    WEIGHT_BIKE_PROB = 0.2
    WEIGHT_COMFORT = 0.15

    def score(self, routes: list[dict]) -> list[dict]:
        """경로 목록에 점수를 매기고 상위 3개를 내림차순으로 반환한다."""
        if not routes:
            return []

        max_time = max(r["estimated_duration_min"] for r in routes)

        scored = []
        for route in routes:
            estimated_min = route["estimated_duration_min"]
            transfers = route.get("transfers", 0)
            bike_probability = route.get("bike_probability", 1.0)
            walk_dist_m = route.get("walk_dist_m", 0.0)

            # 빠를수록 높음 (max_time이 0이면 나누기 방지)
            speed_score = (
                1.0 - (estimated_min / max_time)
                if max_time > 0
                else 1.0
            )

            # 환승 적을수록 높음
            reliability_score = 1.0 / (1.0 + transfers * 0.3)

            # 도보 짧을수록 높음 (2000m 기준 정규화)
            comfort_score = 1.0 - min(walk_dist_m / 2000.0, 1.0)

            total = (
                self.WEIGHT_SPEED * speed_score
                + self.WEIGHT_RELIABILITY * reliability_score
                + self.WEIGHT_BIKE_PROB * bike_probability
                + self.WEIGHT_COMFORT * comfort_score
            )

            scored.append({
                **route,
                "score": round(total, 4),
                "speed_score": round(speed_score, 4),
                "reliability_score": round(reliability_score, 4),
                "comfort_score": round(comfort_score, 4),
            })

            logger.debug(
                "경로 점수화: type={}, total={:.4f}, speed={:.4f}, rel={:.4f}, bike={:.4f}, comfort={:.4f}",
                route.get("type"), total, speed_score, reliability_score,
                bike_probability, comfort_score,
            )

        # 내림차순 정렬 후 상위 3개 반환
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:3]
