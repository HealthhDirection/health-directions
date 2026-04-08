"""경로 추천 API."""

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from app.db.connection import get_pg_connection, get_redis
from app.engine.bike_predictor import BikePredictor
from app.engine.route_finder import RouteFinder
from app.engine.route_scorer import RouteScorer
from app.engine.time_estimator import TimeEstimator

router = APIRouter(tags=["routes"])


@router.get("/routes")
def get_routes(
    origin_lat: float = Query(..., description="출발지 위도"),
    origin_lng: float = Query(..., description="출발지 경도"),
    dest_lat: float = Query(..., description="도착지 위도"),
    dest_lng: float = Query(..., description="도착지 경도"),
):
    """출발지~도착지 최적 경로 2~3개를 추천한다."""
    try:
        pg = get_pg_connection()
        redis = get_redis()
    except Exception as e:
        logger.error("DB/Redis 연결 실패: {}", str(e))
        raise HTTPException(status_code=503, detail="데이터베이스 연결에 실패했습니다.")

    try:
        finder = RouteFinder(pg, redis)
        estimator = TimeEstimator(redis)
        predictor = BikePredictor(redis)
        scorer = RouteScorer()

        # 1. 경로 후보 생성
        routes = finder.find_routes(origin_lat, origin_lng, dest_lat, dest_lng)

        if not routes:
            logger.info(
                "경로 없음: origin=({}, {}), dest=({}, {})",
                origin_lat, origin_lng, dest_lat, dest_lng,
            )
            return {"routes": [], "message": "경로를 찾을 수 없습니다."}

        # 2. 각 후보 시간 추정 및 자전거 가용 확률 계산
        for route in routes:
            route["estimated_duration_min"] = estimator.estimate(route)

            bike_station = route.get("bike_station")
            if bike_station:
                station_id = str(bike_station.get("station_id", ""))
                route["bike_probability"] = predictor.predict_availability(
                    station_id,
                    minutes_ahead=int(route["estimated_duration_min"]),
                )
            else:
                # 자전거 없는 경로는 확률 1.0 (영향 없음)
                route["bike_probability"] = 1.0

        # 3. 점수화 및 상위 3개 반환
        scored_routes = scorer.score(routes)

        return {"routes": scored_routes}

    except Exception as e:
        logger.error("경로 추천 처리 오류: {}", str(e))
        raise HTTPException(status_code=500, detail="경로 추천 중 오류가 발생했습니다.")

    finally:
        try:
            pg.close()
        except Exception:
            pass
