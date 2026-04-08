"""데이터 신선도 확인 API."""

from typing import Any

from fastapi import APIRouter, HTTPException
from loguru import logger

from app.db.connection import get_pg_connection

router = APIRouter(tags=["status"])

COLLECTORS = ["bus", "bike", "signal"]


@router.get("/status")
def get_data_status() -> dict[str, Any]:
    """각 수집기의 최신 수집 시각과 상태를 반환한다."""
    try:
        conn = get_pg_connection()
        try:
            result: dict[str, Any] = {}
            with conn.cursor() as cur:
                for collector in COLLECTORS:
                    # history.collector_log에서 각 collector의 최신 레코드 조회
                    cur.execute(
                        """
                        SELECT status, records_count, collected_at
                        FROM history.collector_log
                        WHERE collector = %s
                        ORDER BY collected_at DESC
                        LIMIT 1
                        """,
                        (collector,),
                    )
                    row = cur.fetchone()
                    if row:
                        result[collector] = {
                            "last_collected": row[2].isoformat() if row[2] else None,
                            "status": row[0],
                            "records_count": row[1],
                        }
                    else:
                        result[collector] = {
                            "last_collected": None,
                            "status": "NOT_STARTED",
                            "records_count": 0,
                        }
        finally:
            conn.close()
    except Exception as db_err:
        logger.error(f"[status] DB 조회 실패: {db_err}")
        raise HTTPException(status_code=500, detail="수집 상태 조회에 실패했습니다.")

    return result
