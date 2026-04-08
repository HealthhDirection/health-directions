"""경로 후보 생성 엔진.

TMAP 대중교통 API를 베이스로,
버스만 / 버스+자전거 / 도보+자전거 조합을 생성한다.
"""

import json

import httpx
from loguru import logger

from app.config import settings
from app.utils.geo import find_nearest, haversine

TMAP_TRANSIT_URL = "https://apis.openapi.sk.com/transit/routes"
BIKE_STATION_SEARCH_RADIUS_M = 400
WALK_ONLY_MAX_DIST_M = 3000
INTERSECTION_SEARCH_RADIUS_M = 100  # 경로 상 교차로 검색 반경

# 교차로 100m 그리드 캐시 설정
# 서울 위도 37.5° 기준: 0.001° ≈ 111m(위도) / 88m(경도)
GRID_STEP = 0.001
GRID_CACHE_TTL = 3600  # 1시간
GRID_POPULATED_KEY = "intersec:grid:v1:populated"


class RouteFinder:
    def __init__(self, pg_conn, redis_client):
        self.pg = pg_conn
        self.redis = redis_client

    def find_routes(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
    ) -> list[dict]:
        """출발~도착 사이 경로 후보를 생성한다."""
        routes: list[dict] = []

        # 1. TMAP 대중교통 경로 조회 (버스만)
        bus_route = self._fetch_tmap_route(origin_lat, origin_lng, dest_lat, dest_lng)
        if bus_route:
            bus_route["type"] = "bus_only"
            bus_route["intersections"] = self._find_intersections_along_route(
                bus_route.get("polyline", [])
            )
            routes.append(bus_route)

            # 2. 도착지 근처 따릉이 대여소 검색 (400m 이내) → 버스+자전거
            bike_station = self._find_nearest_bike_station(dest_lat, dest_lng)
            if bike_station:
                bus_bike_route = {**bus_route}
                bus_bike_route["type"] = "bus_bike"
                bus_bike_route["bike_station"] = bike_station
                bus_bike_route["bike_dist_m"] = bike_station["distance_m"]
                routes.append(bus_bike_route)

        # 3. 직선거리 3km 미만이면 도보+자전거 경로 추가
        direct_dist = haversine(origin_lat, origin_lng, dest_lat, dest_lng)
        if direct_dist < WALK_ONLY_MAX_DIST_M:
            walk_bike_station = self._find_nearest_bike_station(origin_lat, origin_lng)
            walk_bike_route = self._build_walk_bike_route(
                origin_lat, origin_lng, dest_lat, dest_lng,
                direct_dist, walk_bike_station,
            )
            routes.append(walk_bike_route)

        return routes

    def _fetch_tmap_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
    ) -> dict | None:
        """TMAP 대중교통 API를 호출하여 기본 경로 정보를 반환한다."""
        if not settings.tmap_app_key:
            logger.warning("TMAP API 키가 설정되지 않았습니다.")
            return None

        payload = {
            "startX": str(origin_lng),
            "startY": str(origin_lat),
            "endX": str(dest_lng),
            "endY": str(dest_lat),
            "reqCoordType": "WGS84GEO",
            "resCoordType": "WGS84GEO",
            "count": 1,
        }
        headers = {"appKey": settings.tmap_app_key}

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(TMAP_TRANSIT_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("TMAP API HTTP 오류: status={}, url={}", e.response.status_code, TMAP_TRANSIT_URL)
            return None
        except httpx.RequestError as e:
            logger.error("TMAP API 요청 실패: {}", str(e))
            return None
        except Exception as e:
            logger.error("TMAP API 알 수 없는 오류: {}", str(e))
            return None

        return self._parse_tmap_response(data)

    def _parse_tmap_response(self, data: dict) -> dict | None:
        """TMAP 응답에서 경로 정보를 파싱한다."""
        try:
            itinerary = data["metaData"]["plan"]["itineraries"][0]
        except (KeyError, IndexError, TypeError):
            logger.warning("TMAP 응답 파싱 실패: 유효한 itinerary 없음")
            return None

        # duration (초) → 분 변환
        duration_min = itinerary.get("duration", 0) / 60.0

        # legs에서 도보 거리 합산 및 환승 수 계산
        legs = itinerary.get("legs", [])
        walk_dist_m = 0.0
        transfers = 0
        polyline: list = []

        for leg in legs:
            mode = leg.get("mode", "")
            if mode == "WALK":
                walk_dist_m += float(leg.get("distance", 0))
            elif mode in ("BUS", "SUBWAY", "RAIL"):
                transfers += 1

            # 좌표 리스트 추출
            points = leg.get("passShape", {}).get("linestring", "")
            if points:
                for coord_str in points.split(" "):
                    parts = coord_str.split(",")
                    if len(parts) == 2:
                        try:
                            polyline.append({
                                "lng": float(parts[0]),
                                "lat": float(parts[1]),
                            })
                        except ValueError:
                            pass

        # 환승 수는 대중교통 leg 수 - 1 (최소 0)
        transfers = max(0, transfers - 1)

        return {
            "tmap_duration_min": round(duration_min, 2),
            "walk_dist_m": walk_dist_m,
            "bike_dist_m": 0.0,
            "bike_station": None,
            "intersections": [],
            "polyline": polyline,
            "transfers": transfers,
        }

    def _find_nearest_bike_station(self, lat: float, lng: float) -> dict | None:
        """Redis 캐시 우선으로 가장 가까운 따릉이 대여소를 반환한다."""
        # 1. Redis 캐시 조회
        stations = self._load_bike_stations_from_redis()

        # 2. 캐시 없으면 DB 조회
        if not stations:
            stations = self._load_bike_stations_from_db()

        if not stations:
            return None

        # 3. 가장 가까운 대여소 탐색
        nearest = find_nearest(
            lat, lng, stations,
            lat_key="latitude", lng_key="longitude",
            max_dist_m=BIKE_STATION_SEARCH_RADIUS_M,
            top_n=1,
        )
        return nearest[0] if nearest else None

    def _load_bike_stations_from_redis(self) -> list[dict]:
        """Redis bike:all_stations 캐시에서 따릉이 대여소 목록을 로드한다."""
        try:
            raw = self.redis.get("bike:all_stations")
            if raw:
                return json.loads(raw)
        except Exception as e:
            logger.warning("Redis 따릉이 대여소 캐시 조회 실패: {}", str(e))
        return []

    def _load_bike_stations_from_db(self) -> list[dict]:
        """DB master.bike_stations 테이블에서 따릉이 대여소 목록을 로드한다."""
        try:
            with self.pg.cursor() as cur:
                cur.execute(
                    "SELECT station_id, station_name, latitude, longitude FROM master.bike_stations"
                )
                rows = cur.fetchall()
                return [
                    {
                        "station_id": row[0],
                        "station_name": row[1],
                        "latitude": float(row[2]),
                        "longitude": float(row[3]),
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error("DB 따릉이 대여소 조회 실패: {}", str(e))
        return []

    def _load_intersections_from_db(self) -> list[dict]:
        """DB master.intersections 테이블에서 경도가 있는 교차로만 로드한다."""
        try:
            with self.pg.cursor() as cur:
                cur.execute(
                    "SELECT intersection_id, intersection_name, latitude, longitude"
                    " FROM master.intersections"
                    " WHERE longitude IS NOT NULL"
                )
                rows = cur.fetchall()
                return [
                    {
                        "intersection_id": row[0],
                        "intersection_name": row[1],
                        "latitude": float(row[2]),
                        "longitude": float(row[3]),
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error("DB 교차로 조회 실패: {}", str(e))
        return []

    # ── 100m 그리드 캐시 메서드 ────────────────────────────────────────────

    def _grid_key(self, lat: float, lng: float) -> str:
        """위경도를 GRID_STEP 단위로 스냅하여 Redis 키를 반환한다."""
        lat_g = round(round(lat / GRID_STEP) * GRID_STEP, 3)
        lng_g = round(round(lng / GRID_STEP) * GRID_STEP, 3)
        return f"intersec:grid:{lat_g:.3f}:{lng_g:.3f}"

    def _populate_intersection_grid(self, intersections: list[dict]) -> None:
        """교차로 목록을 100m 그리드로 분할하여 Redis 파이프라인으로 캐시한다."""
        grid: dict[str, list[dict]] = {}
        for inter in intersections:
            key = self._grid_key(inter["latitude"], inter["longitude"])
            grid.setdefault(key, []).append(inter)

        try:
            pipe = self.redis.pipeline()
            for key, items in grid.items():
                pipe.setex(key, GRID_CACHE_TTL, json.dumps(items))
            pipe.setex(GRID_POPULATED_KEY, GRID_CACHE_TTL, "1")
            pipe.execute()
            logger.debug("교차로 그리드 캐시 저장: {} 셀", len(grid))
        except Exception as e:
            logger.warning("교차로 그리드 캐시 파이프라인 실패: {}", e)

    def _ensure_intersection_grid(self) -> bool:
        """그리드 캐시 미존재 시 DB에서 로드하여 채운다. 성공 여부를 반환한다."""
        try:
            if self.redis.get(GRID_POPULATED_KEY):
                return True
        except Exception:
            pass

        intersections = self._load_intersections_from_db()
        if not intersections:
            return False
        self._populate_intersection_grid(intersections)
        return True

    def _query_intersection_grid(self, lat: float, lng: float) -> list[dict]:
        """주어진 좌표 주변 3x3 그리드 셀에서 교차로 후보를 반환한다."""
        base_lat = round(round(lat / GRID_STEP) * GRID_STEP, 3)
        base_lng = round(round(lng / GRID_STEP) * GRID_STEP, 3)

        keys = [
            self._grid_key(
                round(base_lat + dlat * GRID_STEP, 3),
                round(base_lng + dlng * GRID_STEP, 3),
            )
            for dlat in (-1, 0, 1)
            for dlng in (-1, 0, 1)
        ]

        candidates: list[dict] = []
        try:
            values = self.redis.mget(keys)
            for raw in values:
                if raw:
                    candidates.extend(json.loads(raw))
        except Exception as e:
            logger.warning("교차로 그리드 캐시 조회 실패: {}", e)
        return candidates

    def _find_intersections_along_route(self, polyline: list[dict]) -> list[dict]:
        """폴리라인 주변 100m 이내 교차로를 중복 없이 반환한다.

        Redis 100m 그리드 캐시 우선 조회, 미캐시 시 DB 로드 후 캐시 저장.
        """
        if not polyline:
            return []

        if not self._ensure_intersection_grid():
            return []

        seen_ids: set[str] = set()
        result: list[dict] = []

        # 폴리라인 포인트 샘플링 (최대 20개)
        step = max(1, len(polyline) // 20)
        sampled = polyline[::step]

        for point in sampled:
            candidates = self._query_intersection_grid(point["lat"], point["lng"])
            nearest = find_nearest(
                point["lat"], point["lng"],
                candidates,
                lat_key="latitude", lng_key="longitude",
                max_dist_m=INTERSECTION_SEARCH_RADIUS_M,
                top_n=3,
            )
            for inter in nearest:
                iid = inter["intersection_id"]
                if iid not in seen_ids:
                    seen_ids.add(iid)
                    result.append(inter)

        return result

    def _build_walk_bike_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        direct_dist_m: float,
        bike_station: dict | None,
    ) -> dict:
        """도보+자전거 경로를 생성한다."""
        # 자전거 대여소까지 도보 거리 + 목적지까지 자전거 거리 추정
        walk_dist_m = 0.0
        bike_dist_m = direct_dist_m

        if bike_station:
            walk_dist_m = bike_station.get("distance_m", 0.0)
            bike_dist_m = haversine(
                bike_station["latitude"], bike_station["longitude"],
                dest_lat, dest_lng,
            )

        # 도보 시간 + 자전거 시간으로 기본 소요시간 추정 (TMAP 없이)
        from app.engine.time_estimator import TimeEstimator
        walk_min = walk_dist_m / TimeEstimator.WALK_SPEED_M_PER_MIN
        bike_min = bike_dist_m / TimeEstimator.BIKE_SPEED_M_PER_MIN
        estimated_min = round(walk_min + bike_min + TimeEstimator.BIKE_RENTAL_MIN, 2)

        return {
            "type": "walk_bike",
            "tmap_duration_min": estimated_min,
            "walk_dist_m": walk_dist_m,
            "bike_dist_m": bike_dist_m,
            "bike_station": bike_station,
            "intersections": [],
            "polyline": [],
            "transfers": 0,
        }
