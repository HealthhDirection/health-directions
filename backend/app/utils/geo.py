"""지리 계산 유틸리티."""

import math


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 좌표 사이의 거리(미터)를 반환한다."""
    R = 6371000  # 지구 반지름 (m)
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def bounding_box(lat: float, lng: float, radius_m: float) -> dict:
    """중심 좌표에서 반경(m) 내 바운딩박스를 반환한다."""
    delta_lat = radius_m / 111320
    delta_lng = radius_m / (111320 * math.cos(math.radians(lat)))
    return {
        "lat_min": lat - delta_lat,
        "lat_max": lat + delta_lat,
        "lng_min": lng - delta_lng,
        "lng_max": lng + delta_lng,
    }


def find_nearest(
    lat: float,
    lng: float,
    candidates: list[dict],
    lat_key: str = "latitude",
    lng_key: str = "longitude",
    max_dist_m: float = float("inf"),
    top_n: int = 1,
) -> list[dict]:
    """
    candidates 리스트에서 (lat, lng)에 가장 가까운 top_n개를 반환한다.
    각 항목에 "distance_m" 필드를 추가한다.
    max_dist_m 이내 항목만 포함한다.
    """
    # 1. 거리 계산 후 필터링
    with_distance = []
    for item in candidates:
        dist = haversine(lat, lng, item[lat_key], item[lng_key])
        if dist <= max_dist_m:
            with_distance.append({**item, "distance_m": dist})

    # 2. 거리 오름차순 정렬 후 top_n 반환
    with_distance.sort(key=lambda x: x["distance_m"])
    return with_distance[:top_n]
