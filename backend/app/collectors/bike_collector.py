"""따릉이 대여소 가용 데이터 수집기."""

import json
from typing import Any

import psycopg2
import redis
from loguru import logger

from app.collectors.base import BaseCollector
from app.utils.korean_api import KoreanApiError, parse_json_response

# 따릉이 API 엔드포인트 (서울 열린데이터 광장)
BIKE_LIST_URL = "http://openapi.seoul.go.kr:8088/{api_key}/json/bikeList/{start}/{end}/"

# 페이지 크기
PAGE_SIZE = 1000

# Redis TTL (초)
REDIS_TTL = 200


class BikeCollector(BaseCollector):
    name = "bike"

    def __init__(self, api_key: str, pg_conn: psycopg2.extensions.connection, redis_client: redis.Redis):
        super().__init__(api_key)
        self.pg_conn = pg_conn
        self.redis_client = redis_client

    def collect(self) -> int:
        """따릉이 전체 대여소 정보를 수집하고 강서구 대여소만 저장한다."""
        # 강서구 대여소 station_id 목록 (필터 기준)
        known_station_ids = self._fetch_known_station_ids()

        all_rows: list[dict[str, Any]] = []
        start = 1

        # 1. 페이지 1000개씩 반복 호출해서 전체 대여소 수집
        while True:
            end = start + PAGE_SIZE - 1
            url = BIKE_LIST_URL.format(api_key=self.api_key, start=start, end=end)
            try:
                resp = self.call_api(url)
                data = parse_json_response(resp)
                rows = data.get("rentBikeStatus", {}).get("row", [])
            except KoreanApiError as e:
                # 데이터 없음 코드는 수집 종료 신호로 처리
                if e.code == "INFO-200":
                    break
                logger.error(f"[bike] API 에러 (start={start}): {e}")
                break
            except Exception as e:
                logger.error(f"[bike] API 호출 실패 (start={start}): {e}")
                break

            if not rows:
                break

            all_rows.extend(rows)

            # 응답 수가 PAGE_SIZE 미만이면 마지막 페이지
            if len(rows) < PAGE_SIZE:
                break
            start += PAGE_SIZE

        if not all_rows:
            logger.warning("[bike] 수집된 데이터 없음")
            return 0

        # 2. 강서구 대여소만 필터
        gangseo_rows = [
            row for row in all_rows
            if "강서" in row.get("stationName", "")
            or row.get("stationId") in known_station_ids
        ]

        if not gangseo_rows:
            logger.warning("[bike] 강서구 해당 대여소 없음")
            return 0

        records: list[dict[str, Any]] = []
        station_cache_list: list[dict[str, Any]] = []

        for row in gangseo_rows:
            station_id: str = row.get("stationId", "")
            station_name: str = row.get("stationName", "")
            available_bikes = self._to_int(row.get("parkingBikeTotCnt"))
            rack_count = self._to_int(row.get("rackTotCnt"))
            available_racks = (rack_count or 0) - (available_bikes or 0)

            record: dict[str, Any] = {
                "station_id": station_id,
                "available_bikes": available_bikes or 0,
                "available_racks": max(available_racks, 0),
            }
            records.append(record)

            cache_entry: dict[str, Any] = {
                "station_id": station_id,
                "station_name": station_name,
                "available_bikes": available_bikes or 0,
                "rack_count": rack_count or 0,
            }
            station_cache_list.append(cache_entry)

            # 4. Redis 개별 대여소 캐시 저장
            try:
                self.redis_client.setex(
                    f"bike:avail:{station_id}",
                    REDIS_TTL,
                    json.dumps(cache_entry, ensure_ascii=False),
                )
            except Exception as redis_err:
                logger.error(f"[bike] Redis 개별 저장 실패 station_id={station_id}: {redis_err}")

        # 5. Redis 강서구 전체 목록 저장
        try:
            self.redis_client.setex(
                "bike:all_stations",
                REDIS_TTL,
                json.dumps(station_cache_list, ensure_ascii=False),
            )
        except Exception as redis_err:
            logger.error(f"[bike] Redis 전체 목록 저장 실패: {redis_err}")

        # 3. realtime.bike_availability에 INSERT
        return self._insert_availability(records)

    def _fetch_known_station_ids(self) -> set[str]:
        """master.bike_stations에서 강서구 대여소 ID 목록을 조회한다."""
        try:
            with self.pg_conn.cursor() as cur:
                cur.execute("SELECT station_id FROM master.bike_stations")
                rows = cur.fetchall()
            return {row[0] for row in rows}
        except Exception as e:
            logger.error(f"[bike] 마스터 대여소 조회 실패: {e}")
            return set()

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
            return len(records)
        except Exception as e:
            self.pg_conn.rollback()
            logger.error(f"[bike] DB INSERT 실패: {e}")
            return 0
