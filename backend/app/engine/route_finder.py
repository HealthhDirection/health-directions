"""경로 후보 생성 엔진.

TMAP 대중교통 API를 베이스로,
버스만 / 버스+자전거 / 도보+자전거 조합을 생성한다.
"""


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
        # TODO: Phase 2에서 구현
        # 1. TMAP 대중교통 경로 조회 (버스만)
        # 2. 도착지 근처 따릉이 대여소 검색 (400m 이내)
        # 3. 버스+자전거 조합 경로 생성
        # 4. 직선거리 3km 미만이면 도보+자전거 경로 추가
        raise NotImplementedError
