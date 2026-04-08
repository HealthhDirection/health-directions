"""교통 신호등 상태 수집기.

https://apis.data.go.kr/B551982/rti/tl_drct_info 기반.
- 서울시 교차로별 8방향 × 6신호 잔여시간 수집
- Redis: signal:{crsrdId} → raw item dict (TTL 200s)
- DB: realtime.signal_state (방향별 보행신호 행 삽입)
"""

import json
from typing import Any

import psycopg2
import redis
from loguru import logger

from app.collectors.base import BaseCollector
from app.utils.korean_api import KoreanApiError, parse_rti_response

RTI_BASE_URL = "https://apis.data.go.kr/B551982/rti"
TL_DRCT_INFO_URL = f"{RTI_BASE_URL}/tl_drct_info"

REDIS_TTL = 200  # seconds
NUM_OF_ROWS = 1000  # per page

# 8방향 접두사
DIRECTIONS = ["nt", "et", "st", "wt", "ne", "se", "sw", "nw"]

# 신호 상태명 → GREEN/RED/YELLOW 매핑 (소문자로 비교)
_PHASE_MAP: dict[str, str] = {
    "protected-movement-allowed": "GREEN",
    "permissive-movement-allowed": "GREEN",
    "stop-and-remain": "RED",
    "protected-clearance": "YELLOW",
    "permissive-clearance": "YELLOW",
}


def _map_phase(raw_status: str) -> str:
    """API 상태명을 GREEN/RED/YELLOW/UNKNOWN으로 변환한다."""
    return _PHASE_MAP.get(raw_status.lower().strip(), "UNKNOWN")


def _decisec_to_sec(value: str | None) -> int | None:
    """데시초(1/10초) 문자열을 정수 초로 변환한다."""
    if not value:
        return None
    try:
        return max(0, int(float(value)) // 10)
    except (ValueError, TypeError):
        return None


class SignalCollector(BaseCollector):
    name = "signal"

    def __init__(self, api_key: str, pg_conn: psycopg2.extensions.connection, redis_client: redis.Redis):
        super().__init__(api_key)
        self.pg_conn = pg_conn
        self.redis_client = redis_client

    def collect(self) -> int:
        """서울시 교차로 신호 잔여시간을 수집하고 저장한다."""
        items = self._fetch_all_signal_items()

        if not items:
            logger.warning("[signal] 신호 데이터 없음")
            return 0

        records: list[dict[str, Any]] = []

        for item in items:
            intersection_id = str(item.get("crsrdId", ""))
            if not intersection_id:
                continue

            # Redis에 교차로별 raw item 캐시 (time_estimator에서 사용)
            try:
                self.redis_client.setex(
                    f"signal:{intersection_id}",
                    REDIS_TTL,
                    json.dumps(item, ensure_ascii=False),
                )
            except Exception as redis_err:
                logger.error(f"[signal] Redis 저장 실패 id={intersection_id}: {redis_err}")

            # 각 방향에서 보행 신호 데이터 추출 → DB 저장용 레코드
            for prefix in DIRECTIONS:
                pd_status = item.get(f"{prefix}PdsgSttsNm", "")
                pd_remain = item.get(f"{prefix}PdsgRmndCs", "")

                if not pd_status and not pd_remain:
                    continue  # 해당 방향 데이터 없음

                records.append({
                    "intersection_id": intersection_id,
                    "direction": prefix,
                    "current_phase": _map_phase(pd_status) if pd_status else "UNKNOWN",
                    "remaining_sec": _decisec_to_sec(pd_remain),
                    "cycle_sec": None,
                })

        if records:
            return self._insert_signal_states(records)
        return 0

    def _fetch_all_signal_items(self) -> list[dict[str, Any]]:
        """RTI /tl_drct_info API를 페이징하여 전체 결과를 반환한다."""
        all_items: list[dict[str, Any]] = []
        page_no = 1

        while True:
            try:
                resp = self.call_api(TL_DRCT_INFO_URL, params={
                    "serviceKey": self.api_key,
                    "pageNo": page_no,
                    "numOfRows": NUM_OF_ROWS,
                    "type": "JSON",
                    "stdgCd": "1100000000",  # 서울특별시 (구 단위 필터 미지원)
                })
                body = parse_rti_response(resp)
            except KoreanApiError as e:
                logger.error(f"[signal] API 에러 (page={page_no}): {e}")
                break
            except Exception as e:
                logger.error(f"[signal] API 호출 실패 (page={page_no}): {e}")
                break

            items = body.get("items", {}).get("item", [])
            if not isinstance(items, list):
                items = [items] if items else []

            if not items:
                break

            all_items.extend(items)

            total_count = int(body.get("totalCount", 0))
            if len(all_items) >= total_count:
                break
            page_no += 1

        logger.info(f"[signal] 총 {len(all_items)}개 교차로 신호 데이터 수집")
        return all_items

    def _insert_signal_states(self, records: list[dict[str, Any]]) -> int:
        """realtime.signal_state에 레코드를 일괄 삽입하고 삽입된 수를 반환한다."""
        sql = """
            INSERT INTO realtime.signal_state
                (intersection_id, direction, current_phase, remaining_sec, cycle_sec)
            VALUES
                (%(intersection_id)s, %(direction)s, %(current_phase)s,
                 %(remaining_sec)s, %(cycle_sec)s)
        """
        try:
            with self.pg_conn.cursor() as cur:
                cur.executemany(sql, records)
            self.pg_conn.commit()
            return len(records)
        except Exception as e:
            self.pg_conn.rollback()
            logger.error(f"[signal] DB INSERT 실패: {e}")
            return 0
