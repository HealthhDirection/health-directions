"""APScheduler 기반 수집 스케줄러."""

import psycopg2
from apscheduler.schedulers.blocking import BlockingScheduler
from loguru import logger

from app.collectors.bike_collector import BikeCollector
from app.collectors.bus_collector import BusCollector
from app.collectors.signal_collector import SignalCollector
from app.config import settings
from app.db.connection import get_pg_connection, get_redis


def _aggregate_bike_hourly(pg_conn: psycopg2.extensions.connection) -> None:
    """직전 1시간 따릉이 가용성을 history.bike_hourly에 시간별로 집계한다.

    ON CONFLICT로 멱등성 보장 — 재실행해도 중복 없음.
    """
    sql = """
        INSERT INTO history.bike_hourly
            (station_id, hour_ts, avg_bikes, min_bikes, max_bikes, sample_count)
        SELECT
            station_id,
            date_trunc('hour', collected_at)        AS hour_ts,
            ROUND(AVG(available_bikes)::numeric, 2) AS avg_bikes,
            MIN(available_bikes)                    AS min_bikes,
            MAX(available_bikes)                    AS max_bikes,
            COUNT(*)                                AS sample_count
        FROM realtime.bike_availability
        WHERE collected_at >= date_trunc('hour', now()) - INTERVAL '2 hours'
          AND collected_at <  date_trunc('hour', now())
        GROUP BY station_id, date_trunc('hour', collected_at)
        ON CONFLICT (station_id, hour_ts) DO UPDATE SET
            avg_bikes    = EXCLUDED.avg_bikes,
            min_bikes    = EXCLUDED.min_bikes,
            max_bikes    = EXCLUDED.max_bikes,
            sample_count = EXCLUDED.sample_count;
    """
    try:
        with pg_conn.cursor() as cur:
            cur.execute(sql)
            row_count = cur.rowcount
        pg_conn.commit()
        logger.info("[aggregate] bike_hourly 집계 완료: {}행 upsert", row_count)
    except Exception as e:
        pg_conn.rollback()
        logger.error("[aggregate] bike_hourly 집계 실패: {}", e)


def create_scheduler() -> tuple[BlockingScheduler, list]:
    """수집 스케줄러를 생성하고 잡을 등록한다.

    반환값: (scheduler, collectors) — 종료 시 collectors에 close() 호출 필요.
    """
    scheduler = BlockingScheduler()

    pg_conn = get_pg_connection()
    redis_client = get_redis()

    bus = BusCollector(
        api_key=settings.bus_api_key,
        location_api_key=settings.signal_api_key,  # 공공데이터포털 키 (RTI API와 동일)
        pg_conn=pg_conn,
        redis_client=redis_client,
    )
    bike = BikeCollector(api_key=settings.bike_api_key, pg_conn=pg_conn, redis_client=redis_client)
    signal = SignalCollector(api_key=settings.signal_api_key, pg_conn=pg_conn, redis_client=redis_client)

    collectors = [bus, bike, signal]

    # 버스: 2분 간격, 06-22시
    scheduler.add_job(bus.run, "cron", minute="*/2", hour="6-21", id="bus_collector")

    # 따릉이: 3분 간격, 06-23시
    scheduler.add_job(bike.run, "cron", minute="*/3", hour="6-22", id="bike_collector")

    # 신호등: 3분 간격, 06-22시
    scheduler.add_job(
        signal.run, "cron", minute="*/3", hour="6-21", id="signal_collector"
    )

    # 따릉이 시간별 집계: 매 시 5분 (직전 시간 데이터가 모두 쌓인 뒤 실행)
    scheduler.add_job(
        _aggregate_bike_hourly,
        "cron",
        minute=5,
        args=[pg_conn],
        id="bike_hourly_aggregate",
    )

    logger.info("수집 스케줄러 등록 완료: bus(2분), bike(3분), signal(3분), bike_hourly집계(매시5분)")
    return scheduler, collectors
