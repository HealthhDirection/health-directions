"""데이터 신선도 확인 API."""

from fastapi import APIRouter

router = APIRouter(tags=["status"])


@router.get("/status")
def get_data_status():
    """각 수집기의 최신 수집 시각과 상태를 반환한다."""
    # TODO: Phase 1에서 구현
    # history.collector_log에서 각 collector의 최신 레코드 조회
    return {
        "bus": {"last_collected": None, "status": "NOT_STARTED"},
        "bike": {"last_collected": None, "status": "NOT_STARTED"},
        "signal": {"last_collected": None, "status": "NOT_STARTED"},
    }
