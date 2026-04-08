"""신호등 데이터 조회 및 수집 테스트 API."""

import json
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from app.config import settings
from app.db.connection import get_redis
from app.utils.korean_api import KoreanApiError, parse_rti_response

router = APIRouter(prefix="/api/signals", tags=["signals"])

RTI_BASE_URL = "https://apis.data.go.kr/B551982/rti"
DIRECTIONS = ["nt", "et", "st", "wt", "ne", "se", "sw", "nw"]
DIRECTION_NAMES = {"nt": "북", "et": "동", "st": "남", "wt": "서", "ne": "북동", "se": "남동", "sw": "남서", "nw": "북서"}


def _parse_item(item: dict) -> dict:
    """raw item에서 8방향 보행 신호 정보를 추출한다."""
    pedestrian = {}
    for prefix in DIRECTIONS:
        status = item.get(f"{prefix}PdsgSttsNm", "")
        remain = item.get(f"{prefix}PdsgRmndCs", "")
        if status or remain:
            sec = int(float(remain)) // 10 if remain else None
            pedestrian[DIRECTION_NAMES[prefix]] = {
                "status": status,
                "remaining_sec": sec,
            }
    return {
        "intersection_id": item.get("crsrdId"),
        "intersection_name": item.get("crsrdNm", ""),
        "pedestrian_signals": pedestrian,
        "updated_at": item.get("totDt"),
    }


@router.get(
    "/live",
    summary="RTI API 직접 호출 (실시간 신호 조회)",
    description=(
        "RTI `/tl_drct_info` API를 직접 호출하여 실시간 신호 데이터를 반환합니다.\n\n"
        "**API 키 우선순위**: `api_key` 파라미터 → 서버 환경변수 `SIGNAL_API_KEY`\n\n"
        "Swagger 테스트 시 `api_key` 필드에 공공데이터포털 인증키를 직접 입력하세요."
    ),
)
def get_live_signals(
    num: int = Query(default=5, ge=1, le=20, description="조회할 교차로 수"),
    api_key: str | None = Query(
        default=None,
        description="공공데이터포털 인증키 (미입력 시 서버 SIGNAL_API_KEY 환경변수 사용)",
    ),
) -> dict[str, Any]:
    """RTI /tl_drct_info API를 직접 호출하여 실시간 신호 데이터를 반환한다."""
    key = api_key or settings.signal_api_key
    if not key:
        raise HTTPException(
            status_code=503,
            detail=(
                "API 키가 없습니다. "
                "Swagger의 api_key 파라미터에 직접 입력하거나, "
                "backend/.env 파일에 SIGNAL_API_KEY=<키> 를 설정하세요."
            ),
        )

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                f"{RTI_BASE_URL}/tl_drct_info",
                params={
                    "serviceKey": key,
                    "pageNo": 1,
                    "numOfRows": num,
                    "type": "JSON",
                    "stdgCd": "1100000000",
                },
            )
            resp.raise_for_status()
            body = parse_rti_response(resp)
    except KoreanApiError as e:
        raise HTTPException(status_code=502, detail=f"RTI API 에러: {e}")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"HTTP 오류: {e}")

    items = body.get("items", {}).get("item", [])
    if not isinstance(items, list):
        items = [items] if items else []

    return {
        "total_count": body.get("totalCount"),
        "returned": len(items),
        "signals": [_parse_item(item) for item in items],
    }


@router.get(
    "/intersections",
    summary="RTI API 직접 호출 (교차로 목록 조회)",
    description=(
        "RTI `/crsrd_map_info` API를 직접 호출하여 교차로 목록을 반환합니다.\n\n"
        "**참고**: 현재 API는 경도(`mapCtptIntLot`)를 빈 값으로 반환합니다. 위도만 제공됩니다.\n\n"
        "Swagger 테스트 시 `api_key` 필드에 공공데이터포털 인증키를 직접 입력하세요."
    ),
)
def get_live_intersections(
    num: int = Query(default=10, ge=1, le=100, description="조회할 교차로 수"),
    api_key: str | None = Query(
        default=None,
        description="공공데이터포털 인증키 (미입력 시 서버 SIGNAL_API_KEY 환경변수 사용)",
    ),
) -> dict[str, Any]:
    """RTI /crsrd_map_info API를 직접 호출하여 교차로 목록을 반환한다."""
    key = api_key or settings.signal_api_key
    if not key:
        raise HTTPException(
            status_code=503,
            detail=(
                "API 키가 없습니다. "
                "Swagger의 api_key 파라미터에 직접 입력하거나, "
                "backend/.env 파일에 SIGNAL_API_KEY=<키> 를 설정하세요."
            ),
        )

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                f"{RTI_BASE_URL}/crsrd_map_info",
                params={
                    "serviceKey": key,
                    "pageNo": 1,
                    "numOfRows": num,
                    "type": "JSON",
                    "stdgCd": "1100000000",
                },
            )
            resp.raise_for_status()
            body = parse_rti_response(resp)
    except KoreanApiError as e:
        raise HTTPException(status_code=502, detail=f"RTI API 에러: {e}")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"HTTP 오류: {e}")

    items = body.get("items", {}).get("item", [])
    if not isinstance(items, list):
        items = [items] if items else []

    return {
        "total_count": body.get("totalCount"),
        "returned": len(items),
        "intersections": [
            {
                "intersection_id": i.get("crsrdId"),
                "intersection_name": i.get("crsrdNm", ""),
                "latitude": i.get("mapCtptIntLat"),
                "longitude": i.get("mapCtptIntLot") or None,
            }
            for i in items
        ],
    }


@router.get("/cache/{intersection_id}", summary="Redis 캐시에서 신호 조회")
def get_cached_signal(intersection_id: str) -> dict[str, Any]:
    """Redis에 캐시된 교차로 신호 데이터를 반환한다. 수집기 실행 후 사용 가능."""
    try:
        redis_client = get_redis()
        raw = redis_client.get(f"signal:{intersection_id}")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis 연결 실패: {e}")

    if raw is None:
        raise HTTPException(
            status_code=404,
            detail=f"교차로 {intersection_id} 캐시 없음. 수집기를 먼저 실행하세요.",
        )

    try:
        item = json.loads(raw)
    except (ValueError, TypeError):
        raise HTTPException(status_code=500, detail="캐시 데이터 파싱 실패")

    return _parse_item(item)
