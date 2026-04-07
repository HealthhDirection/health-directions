"""경로 추천 API."""

from fastapi import APIRouter, Query

router = APIRouter(tags=["routes"])


@router.get("/routes")
def get_routes(
    origin_lat: float = Query(..., description="출발지 위도"),
    origin_lng: float = Query(..., description="출발지 경도"),
    dest_lat: float = Query(..., description="도착지 위도"),
    dest_lng: float = Query(..., description="도착지 경도"),
):
    """출발지~도착지 최적 경로 2~3개를 추천한다."""
    # TODO: Phase 2에서 구현
    # 1. RouteFinder.find_routes()
    # 2. TimeEstimator.estimate() 각 후보
    # 3. BikePredictor.predict_availability() 자전거 포함 경로
    # 4. RouteScorer.score() 점수화
    # 5. 상위 3개 반환
    return {"routes": [], "message": "Phase 2에서 구현 예정"}
