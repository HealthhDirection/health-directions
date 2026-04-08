"""공영자전거(따릉이) 대여소 데이터 수집기.

공공데이터포털 pbdo_v2 API 기반:
- /inf_101_00010001_v2 - 대여소 정보
- /inf_101_00010002_v2 - 현재 대여가능 자전거 수
"""

import json
from typing import Any

import psycopg2
import redis
from loguru import logger

from app.collectors.base import BaseCollector
from app.utils.korean_api import KoreanApiError, parse_json_response

# 공공데이터포털 자전거 API 엔드포인트
PBDO_BASE_URL = "https://apis.data.go.kr/B551982/pbdo_v2"
BIKE_STATION_INFO_URL = f"{PBDO_BASE_URL}/inf_101_00010001_v2"
BIKE_AVAILABILITY_URL = f"{PBDO_BASE_URL}/inf_101_00010002_v2"

# 지자체 코드: 서울시 (강서구는 좌표 필터링으로 처리)
SEOUL_LGCVMN_CD = "1100000000"

# 강서구 좌표 범위
GANGSEO_LAT_MIN = 37.53
GANGSEO_LAT_MAX = 37.58
GANGSEO_LNG_MIN = 126.80
GANGSEO_LNG_MAX = 126.88

# 페이지 크기
PAGE_SIZE = 1000

# Redis TTL (초)
REDIS_TTL_STATION = 86400  # 마스터: 24시간
REDIS_TTL_AVAILABILITY = 180  # 가용성: 3분


class BikeCollector(BaseCollector):
    name = "bike"

    def __init__(self, api_key: str, pg_conn: psycopg2.extensions.connection, redis_client: redis.Redis):
        super().__init__(api_key)
        self.pg_conn = pg_conn
        self.redis_client = redis_client

    def collect(self) -> int:
        """공공데이터포털 API에서 따릉이 대여가능 현황을 수집하고 저장한다."""
        total_saved = 0

        # 1. 대여가능 현황 수집 (매번 수집)
        availability_count = self._collect_availability()
        total_saved += availability_count

        return total_saved

    def _collect_availability(self) -> int:
        """공공데이터포털에서 현재 대여가능 자전거 수를 수집한다."""
        all_items: list[dict[str, Any]] = []
        page_no = 1

        # 1. 페이징으로 전체 대여소 조회
        while True:
            try:
                resp = self.call_api(BIKE_AVAILABILITY_URL, params={
                    "serviceKey": self.api_key,
                    "lcgvmnInstCd": SEOUL_LGCVMN_CD,
                    "pageNo": page_no,
                    "numOfRows": PAGE_SIZE,
                    "type": "JSON",
                })
                data = parse_json_response(resp)
            except KoreanApiError as e:
                logger.error(f"[bike] 가용성 API 에러 (page={page_no}): {e}")
                break
            except Exception as e:
                logger.error(f"[bike] 가용성 API 호출 실패 (page={page_no}): {e}")
                break

            items = data.get("body", {}).get("item", [])
            if not isinstance(items, list):
                items = [items] if items else []

            if not items:
                break

            all_items.extend(items)

            # 응답 수가 PAGE_SIZE 미만이면 마지막 페이지
            total_count = int(data.get("body", {}).get("totalCount", 0))
            if len(all_items) >= total_count:
                break
            page_no += 1

        if not all_items:
            logger.warning("[bike] 대여가능 현황 데이터 없음")
            return 0

        # 2. 강서구 범위로 필터링
        gangseo_items = [
            item for item in all_items
            if self._in_gangseo_range(item.get("lat"), item.get("lot"))
        ]

        if not gangseo_items:
            logger.warning("[bike] 강서구 범위 내 대여소 없음")
            return 0

        records: list[dict[str, Any]] = []
        for item in gangseo_items:
            station_id: str = item.get("rntstnId", "")
            if not station_id:
                continue

            available_bikes = self._to_int(item.get("bcyclTpkctNocs", 0))

            # DB에 저장할 레코드
            record: dict[str, Any] = {
                "station_id": station_id,
                "available_bikes": available_bikes or 0,
                "available_racks": 0,  # 반납 가능 수는 master에서 계산
            }
            records.append(record)

            # 3. Redis 개별 대여소 캐시 저장
            cache_entry: dict[str, Any] = {
                "station_id": station_id,
                "station_name": item.get("rntstnNm", ""),
                "available_bikes": available_bikes or 0,
                "latitude": item.get("lat"),
                "longitude": item.get("lot"),
            }
            try:
                self.redis_client.setex(
                    f"bike:avail:{station_id}",
                    REDIS_TTL_AVAILABILITY,
                    json.dumps(cache_entry, ensure_ascii=False),
                )
            except Exception as redis_err:
                logger.error(f"[bike] Redis 저장 실패 station_id={station_id}: {redis_err}")

        # 4. realtime.bike_availability에 INSERT
        if records:
            return self._insert_availability(records)
        return 0

    def _in_gangseo_range(self, lat: str | float | None, lng: str | float | None) -> bool:
        """좌표가 강서구 범위 내에 있는지 확인한다."""
        if not lat or not lng:
            return False
        try:
            lat_f = float(lat)
            lng_f = float(lng)
            return (
                GANGSEO_LAT_MIN <= lat_f <= GANGSEO_LAT_MAX
                and GANGSEO_LNG_MIN <= lng_f <= GANGSEO_LNG_MAX
            )
        except (ValueError, TypeError):
            return False

    def _to_int(self, value: Any) -> int | None:
        """문자열 또는 숫자를 int로 변환한다. 변환 불가 시 None 반환."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _insert_availability(self, records: list[dict[str, Any]]) -> int:
        """realtime.bike_availability에 레코드를 일괄 삽입하고 삽입된 수를 반환한다."""
        sql = """
            INSERT INTO realtime.bike_availability (station_id, available_bikes, available_racks)
            VALUES (%(station_id)s, %(available_bikes)s, %(available_racks)s)
        """
        try:
            with self.pg_conn.cursor() as cur:
                cur.executemany(sql, records)
            self.pg_conn.commit()
            logger.info(f"[bike] {len(records)}개 대여소 가용성 저장 완료")
            return len(records)
        except Exception as e:
            self.pg_conn.rollback()
            logger.error(f"[bike] 가용성 INSERT 실패: {e}")
            return 0
