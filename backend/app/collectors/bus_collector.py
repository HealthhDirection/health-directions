"""버스 도착/위치 데이터 수집기."""

import json
from typing import Any

import psycopg2
import redis
from loguru import logger

from app.collectors.base import BaseCollector
from app.utils.korean_api import KoreanApiError, parse_xml_response

# 버스 도착 정보 API 엔드포인트 (서울시)
BUS_ARRIVAL_URL = "http://ws.bus.go.kr/api/rest/arrinfo/getStaionByUid"

# 버스 실시간 위치 API 엔드포인트 (공공데이터포털)
BUS_LOCATION_API_URL = "https://apis.data.go.kr/B551982/rte/rtm_loc_info"

# 지자체 코드: 강서구 (시 단위: 서울시)
SEOUL_STDG_CD = "1100000000"

# Redis TTL (초)
REDIS_TTL_ARRIVAL = 150
REDIS_TTL_LOCATION = 60


class BusCollector(BaseCollector):
    name = "bus"

    def __init__(
        self,
        api_key: str,
        location_api_key: str,
        pg_conn: psycopg2.extensions.connection,
        redis_client: redis.Redis,
    ):
        super().__init__(api_key)
        self.location_api_key = location_api_key
        self.pg_conn = pg_conn
        self.redis_client = redis_client

    def collect(self) -> int:
        """강서구 버스 정류장별 도착 정보 + 실시간 위치 정보를 수집하고 저장한다."""
        total_saved = 0

        # 1. 도착 정보 수집
        arrival_count = self._collect_arrivals()
        total_saved += arrival_count

        # 2. 실시간 위치 정보 수집
        location_count = self._collect_realtime_locations()
        total_saved += location_count

        return total_saved

    def _collect_arrivals(self) -> int:
        """각 정류장별 버스 도착 정보를 수집하고 저장한다."""
        # 1. master.bus_stops에서 강서구 정류장 목록 조회
        stops = self._fetch_bus_stops()
        if not stops:
            logger.warning("[bus] 강서구 정류장 데이터 없음. seed 스크립트 실행 필요.")
            return 0

        records: list[dict[str, Any]] = []

        # 2. 각 정류장별 버스 도착 API 호출
        for stop in stops:
            stop_id: str = stop["stop_id"]
            try:
                resp = self.call_api(BUS_ARRIVAL_URL, params={
                    "ServiceKey": self.api_key,
                    "arsId": stop_id,
                })
                root = parse_xml_response(resp.content)
                items = root.findall(".//itemList")

                for item in items:
                    parsed = self._parse_arrival_item(item, stop_id)
                    records.append(parsed)

                    # 5. Redis 개별 정류장 캐시 저장
                    cache_key = f"bus:arr:{stop_id}"
                    try:
                        existing_raw = self.redis_client.get(cache_key)
                        existing: list[dict[str, Any]] = json.loads(existing_raw) if existing_raw else []
                        existing.append(parsed)
                        self.redis_client.setex(cache_key, REDIS_TTL_ARRIVAL, json.dumps(existing, ensure_ascii=False))
                    except Exception as redis_err:
                        logger.error(f"[bus] Redis 저장 실패 stop_id={stop_id}: {redis_err}")

            except KoreanApiError as e:
                logger.error(f"[bus] 도착정보 API 에러 stop_id={stop_id}: {e}")
                continue
            except Exception as e:
                logger.error(f"[bus] 정류장 도착정보 수집 실패 stop_id={stop_id}: {e}")
                continue

        # 4. realtime.bus_arrivals에 INSERT
        if records:
            return self._insert_arrivals(records)
        return 0

    def _collect_realtime_locations(self) -> int:
        """공공데이터포털 API에서 버스 실시간 위치 정보를 수집한다."""
        try:
            resp = self.call_api(BUS_LOCATION_API_URL, params={
                "serviceKey": self.location_api_key,
                "stdgCd": SEOUL_STDG_CD,
                "pageNo": 1,
                "numOfRows": 1000,
                "type": "JSON",
            })
            data = resp.json()

            # API 응답 검증
            if data.get("header", {}).get("resultCode") != "K0":
                logger.warning(f"[bus] 실시간 위치 API 오류: {data.get('header', {}).get('resultMsg')}")
                return 0

            body = data.get("body", {})
            items = body.get("items", {}).get("item", [])
            if not isinstance(items, list):
                items = [items] if items else []

            records: list[dict[str, Any]] = []
            for item in items:
                parsed = self._parse_location_item(item)
                if parsed:
                    records.append(parsed)

                    # Redis에 버스별 위치 캐시 저장
                    cache_key = f"bus:loc:{item['vhclNo']}"
                    try:
                        self.redis_client.setex(
                            cache_key,
                            REDIS_TTL_LOCATION,
                            json.dumps({
                                "route_id": parsed.get("route_id"),
                                "latitude": parsed.get("latitude"),
                                "longitude": parsed.get("longitude"),
                                "direction_angle": parsed.get("direction_angle"),
                                "speed_kmh": parsed.get("speed_kmh"),
                                "collected_at": str(parsed.get("collected_at")),
                            }, ensure_ascii=False),
                        )
                    except Exception as redis_err:
                        logger.error(f"[bus] Redis 위치 캐시 저장 실패 vhclNo={item['vhclNo']}: {redis_err}")

            # realtime.bus_positions에 INSERT
            if records:
                return self._insert_locations(records)
            return 0

        except Exception as e:
            logger.error(f"[bus] 실시간 위치 정보 수집 실패: {e}")
            return 0

    def _fetch_bus_stops(self) -> list[dict[str, str]]:
        """master.bus_stops에서 강서구 정류장 목록을 조회한다."""
        with self.pg_conn.cursor() as cur:
            cur.execute("SELECT stop_id FROM master.bus_stops")
            rows = cur.fetchall()
        return [{"stop_id": row[0]} for row in rows]

    def _parse_arrival_item(self, item: Any, stop_id: str) -> dict[str, Any]:
        """XML itemList element를 도착 정보 dict로 변환한다."""
        def get_text(tag: str) -> str | None:
            el = item.find(tag)
            return el.text.strip() if el is not None and el.text else None

        def get_int(tag: str) -> int | None:
            val = get_text(tag)
            if val is None:
                return None
            try:
                return int(val)
            except ValueError:
                return None

        ars_id = get_text("arsId") or stop_id

        return {
            "stop_id": ars_id,
            "route_id": get_text("busRouteId"),
            "arrival_sec_1": get_int("traTime1"),
            "arrival_sec_2": get_int("traTime2"),
            "bus_id_1": get_text("plainNo1"),
            "bus_id_2": get_text("plainNo2"),
            "congestion_1": get_int("reride_Num1"),
        }

    def _parse_location_item(self, item: dict[str, Any]) -> dict[str, Any] | None:
        """공공데이터포털 RTI 데이터를 위치 정보 dict로 변환한다."""
        try:
            # 필수 필드 검증
            vehicle_no = item.get("vhclNo")
            if not vehicle_no:
                return None

            route_id = item.get("rteId")
            lat = float(item.get("lat", 0))
            lng = float(item.get("lot", 0))
            direction = int(item.get("oprDrct", 0))
            speed = int(item.get("oprSpd", 0))

            # 위도/경도 유효성 검사
            if not (33 <= lat <= 38 and 124 <= lng <= 129):  # 한국 범위
                logger.warning(f"[bus] 유효하지 않은 좌표 vhclNo={vehicle_no}: lat={lat}, lng={lng}")
                return None

            return {
                "route_id": route_id,
                "bus_id": vehicle_no,
                "latitude": lat,
                "longitude": lng,
                "direction_angle": direction,
                "speed_kmh": speed,
                "collected_at": item.get("gthrDt"),
            }
        except (ValueError, KeyError) as e:
            logger.error(f"[bus] 위치 데이터 파싱 실패: {e}")
            return None

    def _insert_arrivals(self, records: list[dict[str, Any]]) -> int:
        """realtime.bus_arrivals에 레코드를 일괄 삽입하고 삽입된 수를 반환한다."""
        sql = """
            INSERT INTO realtime.bus_arrivals
                (stop_id, route_id, arrival_sec_1, arrival_sec_2, bus_id_1, bus_id_2, congestion_1)
            VALUES
                (%(stop_id)s, %(route_id)s, %(arrival_sec_1)s, %(arrival_sec_2)s,
                 %(bus_id_1)s, %(bus_id_2)s, %(congestion_1)s)
        """
        try:
            with self.pg_conn.cursor() as cur:
                cur.executemany(sql, records)
            self.pg_conn.commit()
            return len(records)
        except Exception as e:
            self.pg_conn.rollback()
            logger.error(f"[bus] 도착정보 INSERT 실패: {e}")
            return 0

    def _insert_locations(self, records: list[dict[str, Any]]) -> int:
        """realtime.bus_positions에 버스 위치 레코드를 일괄 삽입한다."""
        sql = """
            INSERT INTO realtime.bus_positions
                (route_id, bus_id, latitude, longitude, collected_at)
            VALUES
                (%(route_id)s, %(bus_id)s, %(latitude)s, %(longitude)s, %(collected_at)s)
        """
        try:
            with self.pg_conn.cursor() as cur:
                cur.executemany(sql, records)
            self.pg_conn.commit()
            return len(records)
        except Exception as e:
            self.pg_conn.rollback()
            logger.error(f"[bus] 위치정보 INSERT 실패: {e}")
            return 0
