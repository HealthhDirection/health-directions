"""정류장/대여소 조회 API."""

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from loguru import logger

from app.db.connection import get_pg_connection, get_redis

router = APIRouter(tags=["stations"])


@router.get("/stations/bike")
def get_bike_stations() -> dict[str, Any]:
    """강서구 따릉이 대여소 목록 + 실시간 가용 수량."""
    # 1. Redis bike:all_stations 캐시 조회
    try:
        redis_client = get_redis()
        cached = redis_client.get("bike:all_stations")
        if cached:
            stations: list[dict[str, Any]] = json.loads(cached)
            return {"stations": stations}
    except Exception as redis_err:
        logger.warning(f"[stations/bike] Redis 조회 실패, DB fallback: {redis_err}")

    # 2. 캐시 없으면 DB 조회
    try:
        conn = get_pg_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        s.station_id,
                        s.station_name,
                        s.latitude,
                        s.longitude,
                        COALESCE(a.available_bikes, 0) AS available_bikes,
                        COALESCE(s.rack_count, 0)      AS rack_count
                    FROM master.bike_stations s
                    LEFT JOIN LATERAL (
                        SELECT available_bikes
                        FROM realtime.bike_availability
                        WHERE station_id = s.station_id
                        ORDER BY collected_at DESC
                        LIMIT 1
                    ) a ON true
                    ORDER BY s.station_name
                    """
                )
                rows = cur.fetchall()
        finally:
            conn.close()
    except Exception as db_err:
        logger.error(f"[stations/bike] DB 조회 실패: {db_err}")
        raise HTTPException(status_code=500, detail="따릉이 대여소 조회에 실패했습니다.")

    stations = [
        {
            "station_id": row[0],
            "station_name": row[1],
            "lat": float(row[2]),
            "lng": float(row[3]),
            "available_bikes": row[4],
            "rack_count": row[5],
        }
        for row in rows
    ]
    return {"stations": stations}


@router.get("/stations/bus")
def get_bus_stops() -> dict[str, Any]:
    """강서구 버스 정류장 목록."""
    try:
        conn = get_pg_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT stop_id, stop_name, latitude, longitude FROM master.bus_stops ORDER BY stop_name"
                )
                rows = cur.fetchall()
        finally:
            conn.close()
    except Exception as db_err:
        logger.error(f"[stations/bus] DB 조회 실패: {db_err}")
        raise HTTPException(status_code=500, detail="버스 정류장 조회에 실패했습니다.")

    stops = [
        {
            "stop_id": row[0],
            "stop_name": row[1],
            "lat": float(row[2]),
            "lng": float(row[3]),
        }
        for row in rows
    ]
    return {"stops": stops}
