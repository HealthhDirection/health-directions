"""마스터 데이터 1회 적재 스크립트.

강서구 버스 정류장과 따릉이 대여소를 수집하여 DB에 저장한다.
실행: python scripts/seed_master_data.py
"""

import sys
from pathlib import Path

# backend 모듈을 PYTHONPATH에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from loguru import logger

from app.config import settings
from app.db.connection import get_pg_connection
from app.utils.korean_api import KoreanApiError, parse_json_response, parse_rti_response, parse_xml_response

import httpx

# 강서구 중심 좌표
GANGSEO_LAT = 37.5509
GANGSEO_LNG = 126.8495
GANGSEO_RADIUS_M = 5000

# 버스 경유지 정보 API (정류소 ID + 좌표 포함)
BUS_PS_INFO_URL = "https://apis.data.go.kr/B551982/rte/ps_info"
GANGSEO_STDG_CD = "1150000000"

# 따릉이 대여소 기본 정보 API (공공데이터포털)
BIKE_STATION_INFO_URL = "https://apis.data.go.kr/B551982/pbdo_v2/inf_101_00010001_v2"
SEOUL_BIKE_STDG_CD = "1100000000"

# 강서구 좌표 범위
GANGSEO_LAT_MIN, GANGSEO_LAT_MAX = 37.53, 37.58
GANGSEO_LNG_MIN, GANGSEO_LNG_MAX = 126.80, 126.88

PAGE_SIZE = 1000


def seed_bus_stops(conn, api_key: str) -> int:
    """강서구 버스 정류장을 master.bus_stops에 UPSERT한다.

    ps_info 엔드포인트에서 노선 경유지 전체를 수집하고
    강서구 좌표 범위로 필터링한다.
    """
    logger.info("버스 정류장 수집 시작 (ps_info 전체 수집 후 강서구 필터)...")

    client = httpx.Client(timeout=15.0)
    seen: dict[str, dict] = {}  # stop_id → record (중복 제거)
    page_no = 1

    try:
        while True:
            try:
                resp = client.get(BUS_PS_INFO_URL, params={
                    "serviceKey": api_key,
                    "pageNo": page_no,
                    "numOfRows": PAGE_SIZE,
                    "type": "JSON",
                })
                resp.raise_for_status()
                body = parse_rti_response(resp)
            except KoreanApiError as e:
                logger.error(f"버스 경유지 API 에러 (page={page_no}): {e}")
                break
            except Exception as e:
                logger.error(f"버스 경유지 API 호출 실패 (page={page_no}): {e}")
                break

            items = body.get("items", {}).get("item", [])
            if not isinstance(items, list):
                items = [items] if items else []
            if not items:
                break

            for item in items:
                stop_id = str(item.get("bstaId", "")).strip()
                stop_name = str(item.get("bstaNm", "")).strip()
                try:
                    lat = float(item.get("bstaLat") or 0)
                    lng = float(item.get("bstaLot") or 0)
                except (ValueError, TypeError):
                    continue

                if not stop_id or not stop_name or lat == 0 or lng == 0:
                    continue
                if not (GANGSEO_LAT_MIN <= lat <= GANGSEO_LAT_MAX and
                        GANGSEO_LNG_MIN <= lng <= GANGSEO_LNG_MAX):
                    continue

                seen[stop_id] = {"stop_id": stop_id, "stop_name": stop_name,
                                 "latitude": lat, "longitude": lng}

            total_count = int(body.get("totalCount", 0))
            if page_no * PAGE_SIZE >= total_count:
                break
            page_no += 1
    finally:
        client.close()

    records = list(seen.values())
    if not records:
        logger.warning("강서구 범위 버스 정류장 없음")
        return 0

    sql = """
        INSERT INTO master.bus_stops (stop_id, stop_name, latitude, longitude)
        VALUES (%(stop_id)s, %(stop_name)s, %(latitude)s, %(longitude)s)
        ON CONFLICT (stop_id) DO UPDATE SET
            stop_name = EXCLUDED.stop_name,
            latitude  = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            updated_at = now()
    """
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, records)
        conn.commit()
        logger.info(f"버스 정류장 {len(records)}건 UPSERT 완료")
        return len(records)
    except Exception as e:
        conn.rollback()
        logger.error(f"버스 정류장 DB UPSERT 실패: {e}")
        return 0


def seed_bike_stations(conn, api_key: str) -> int:
    """강서구 따릉이 대여소를 master.bike_stations에 UPSERT한다.

    공공데이터포털 pbdo_v2/inf_101_00010001_v2에서 서울시 전체를 수집하고
    강서구 좌표 범위로 필터링한다.
    """
    logger.info("따릉이 대여소 수집 시작 (pbdo_v2 inf_101_00010001_v2)...")

    client = httpx.Client(timeout=15.0)
    all_items: list[dict] = []
    page_no = 1

    try:
        while True:
            try:
                resp = client.get(BIKE_STATION_INFO_URL, params={
                    "serviceKey": api_key,
                    "lcgvmnInstCd": SEOUL_BIKE_STDG_CD,
                    "pageNo": page_no,
                    "numOfRows": PAGE_SIZE,
                    "type": "JSON",
                })
                resp.raise_for_status()
                body = parse_rti_response(resp)
            except KoreanApiError as e:
                if e.code in ("INFO-200", "03"):
                    break
                logger.error(f"따릉이 API 에러 (page={page_no}): {e}")
                break
            except Exception as e:
                logger.error(f"따릉이 API 호출 실패 (page={page_no}): {e}")
                break

            items = body.get("item", [])
            if not isinstance(items, list):
                items = [items] if items else []
            if not items:
                break

            all_items.extend(items)

            total_count = int(body.get("totalCount", 0))
            if page_no * PAGE_SIZE >= total_count:
                break
            page_no += 1
    finally:
        client.close()

    records = []
    for item in all_items:
        station_id = str(item.get("rntstnId", "")).strip()
        station_name = str(item.get("rntstnNm", "")).strip()
        try:
            lat = float(item.get("lat") or 0)
            lng = float(item.get("lot") or 0)
        except (ValueError, TypeError):
            continue

        if not station_id or not station_name or lat == 0 or lng == 0:
            continue
        if not (GANGSEO_LAT_MIN <= lat <= GANGSEO_LAT_MAX and
                GANGSEO_LNG_MIN <= lng <= GANGSEO_LNG_MAX):
            continue

        records.append({
            "station_id": station_id,
            "station_name": station_name,
            "latitude": lat,
            "longitude": lng,
            "rack_count": 0,
        })

    if not records:
        logger.warning("강서구 범위 따릉이 대여소 없음")
        return 0

    sql = """
        INSERT INTO master.bike_stations (station_id, station_name, latitude, longitude, rack_count)
        VALUES (%(station_id)s, %(station_name)s, %(latitude)s, %(longitude)s, %(rack_count)s)
        ON CONFLICT (station_id) DO UPDATE SET
            station_name = EXCLUDED.station_name,
            latitude     = EXCLUDED.latitude,
            longitude    = EXCLUDED.longitude,
            rack_count   = EXCLUDED.rack_count
    """
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, records)
        conn.commit()
        logger.info(f"따릉이 대여소 {len(records)}건 UPSERT 완료")
        return len(records)
    except Exception as e:
        conn.rollback()
        logger.error(f"따릉이 대여소 DB UPSERT 실패: {e}")
        return 0


# RTI 교차로 맵 API
# stdgCd: RTI API는 지자체 코드를 시(市) 단위만 지원. 구 단위 코드로는 빈 결과 반환.
RTI_BASE_URL = "https://apis.data.go.kr/B551982/rti"
RTI_CRSRD_MAP_URL = f"{RTI_BASE_URL}/crsrd_map_info"
SEOUL_STDG_CD = "1100000000"  # 서울특별시 — RTI API가 지원하는 최소 단위

# TMAP POI 검색 (경도 보완용)
TMAP_POIS_URL = "https://apis.openapi.sk.com/tmap/pois"


def _geocode_longitude_tmap(name: str, lat_hint: float, tmap_app_key: str, client: httpx.Client) -> float | None:
    """TMAP POI 검색으로 교차로명의 경도를 조회한다.

    RTI API가 경도(mapCtptIntLot)를 미제공하므로 교차로명 + 위도로 보완.
    반환값이 None이면 geocoding 실패를 의미한다.
    """
    try:
        resp = client.get(
            TMAP_POIS_URL,
            params={
                "version": "1",
                "searchKeyword": name,
                "appKey": tmap_app_key,
                "count": 5,
            },
            timeout=5.0,
        )
        resp.raise_for_status()
        data = resp.json()
        pois = data.get("searchPoiInfo", {}).get("pois", {}).get("poi", [])
        if not pois:
            return None

        # 위도가 가장 가까운 POI 선택
        best_lng: float | None = None
        best_diff = float("inf")
        for poi in pois:
            try:
                poi_lat = float(poi.get("noorLat", 0))
                poi_lng = float(poi.get("noorLon", 0))
            except (ValueError, TypeError):
                continue
            diff = abs(poi_lat - lat_hint)
            if diff < best_diff:
                best_diff = diff
                best_lng = poi_lng

        # 위도 차이가 0.05도 이상이면 너무 멀어서 제외
        if best_diff > 0.05:
            return None
        return best_lng
    except Exception as e:
        logger.debug(f"TMAP geocoding 실패 ({name}): {e}")
        return None


def seed_intersections(conn, api_key: str) -> int:
    """서울시 교차로를 수집해 강서구 범위로 필터링, master.intersections에 UPSERT한다.

    RTI API /crsrd_map_info:
    - stdgCd는 시(市) 단위만 지원 → "1100000000" (서울특별시) 사용
    - mapCtptIntLot(경도)가 API에서 빈 값으로 반환됨
      → settings.tmap_app_key가 있으면 TMAP POI 검색으로 보완
    """
    logger.info("교차로 수집 시작 (서울시 전체 조회 후 강서구 필터)...")

    client = httpx.Client(timeout=15.0)
    all_items: list[dict] = []
    page_no = 1
    num_of_rows = 1000

    try:
        while True:
            try:
                resp = client.get(
                    RTI_CRSRD_MAP_URL,
                    params={
                        "serviceKey": api_key,
                        "pageNo": page_no,
                        "numOfRows": num_of_rows,
                        "type": "JSON",
                        "stdgCd": SEOUL_STDG_CD,
                    },
                )
                resp.raise_for_status()
                body = parse_rti_response(resp)
            except KoreanApiError as e:
                logger.error(f"교차로 API 에러: {e}")
                break
            except Exception as e:
                logger.error(f"교차로 API 호출 실패: {e}")
                break

            raw_items = body.get("items", {}).get("item", [])
            if not isinstance(raw_items, list):
                raw_items = [raw_items] if raw_items else []
            if not raw_items:
                break

            all_items.extend(raw_items)

            total_count = int(body.get("totalCount", 0))
            if len(all_items) >= total_count:
                break
            page_no += 1
    finally:
        client.close()

    if not all_items:
        logger.warning("교차로 API 응답 데이터 없음 — SIGNAL_API_KEY 확인 필요")
        return 0

    logger.info(f"서울시 교차로 총 {len(all_items)}건 수신, 강서구 범위 필터링 중...")

    # 강서구 위도 범위로 1차 필터 (경도 미제공이므로 위도만 사용)
    lat_min = settings.gangseo_lat_min
    lat_max = settings.gangseo_lat_max
    filtered = []
    for item in all_items:
        try:
            lat = float(item.get("mapCtptIntLat") or 0)
        except (ValueError, TypeError):
            continue
        if lat == 0 or not (lat_min <= lat <= lat_max):
            continue
        filtered.append(item)

    if not filtered:
        logger.warning(
            f"강서구 위도 범위({lat_min}~{lat_max}) 내 교차로 없음. "
            "API 응답 lat 범위 확인 필요."
        )
        return 0

    logger.info(f"강서구 범위 교차로 {len(filtered)}건, TMAP 경도 보완 시작...")

    # TMAP geocoding으로 경도 보완 (tmap_app_key가 있을 때만)
    tmap_client = httpx.Client(timeout=5.0)
    tmap_key = settings.tmap_app_key
    geocoded = 0

    records = []
    for item in filtered:
        intersection_id = str(item.get("crsrdId", ""))
        name = item.get("crsrdNm", "")
        try:
            lat = float(item.get("mapCtptIntLat") or 0)
        except (ValueError, TypeError):
            continue

        lng: float | None = None
        if tmap_key and name:
            lng = _geocode_longitude_tmap(name, lat, tmap_key, tmap_client)
            if lng is not None:
                geocoded += 1

        records.append({
            "intersection_id": intersection_id,
            "intersection_name": name,
            "latitude": lat,
            "longitude": lng,
        })

    tmap_client.close()
    logger.info(f"TMAP geocoding: {geocoded}/{len(records)}건 경도 보완 완료")

    if not records:
        logger.warning("저장할 교차로 레코드 없음")
        return 0

    sql = """
        INSERT INTO master.intersections
            (intersection_id, intersection_name, latitude, longitude)
        VALUES
            (%(intersection_id)s, %(intersection_name)s, %(latitude)s, %(longitude)s)
        ON CONFLICT (intersection_id) DO UPDATE SET
            intersection_name = EXCLUDED.intersection_name,
            latitude          = EXCLUDED.latitude,
            longitude         = COALESCE(EXCLUDED.longitude, master.intersections.longitude)
    """
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, records)
        conn.commit()
        logger.info(f"교차로 {len(records)}건 UPSERT 완료 (경도 있음: {geocoded}건)")
        return len(records)
    except Exception as e:
        conn.rollback()
        logger.error(f"교차로 DB UPSERT 실패: {e}")
        return 0


def main():
    logger.info("마스터 데이터 적재 시작")

    conn = get_pg_connection()
    try:
        bus_count = seed_bus_stops(conn, settings.bus_api_key)
        bike_count = seed_bike_stations(conn, settings.bike_api_key)
        intersection_count = seed_intersections(conn, settings.signal_api_key)

        logger.info(
            f"적재 완료 - 버스 정류장: {bus_count}건, "
            f"따릉이 대여소: {bike_count}건, "
            f"교차로: {intersection_count}건"
        )

        if bus_count == 0:
            logger.warning("버스 정류장 적재 실패. BUS_API_KEY 확인 필요.")
        if bike_count == 0:
            logger.warning("따릉이 대여소 적재 실패. BIKE_API_KEY 확인 필요.")
        if intersection_count == 0:
            logger.warning(
                "교차로 적재 0건. SIGNAL_API_KEY 확인 또는 "
                "위도 범위(37.53~37.58) 내 교차로 없음."
            )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
