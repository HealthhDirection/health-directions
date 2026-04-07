"""APScheduler 기반 수집 스케줄러."""

from apscheduler.schedulers.blocking import BlockingScheduler
from loguru import logger

from app.collectors.bike_collector import BikeCollector
from app.collectors.bus_collector import BusCollector
from app.collectors.signal_collector import SignalCollector
from app.config import settings


def create_scheduler() -> BlockingScheduler:
    """수집 스케줄러를 생성하고 잡을 등록한다."""
    scheduler = BlockingScheduler()

    bus = BusCollector(api_key=settings.bus_api_key)
    bike = BikeCollector(api_key=settings.bike_api_key)
    signal = SignalCollector(api_key=settings.signal_api_key)

    # 버스: 2분 간격, 06-22시
    scheduler.add_job(bus.run, "cron", minute="*/2", hour="6-21", id="bus_collector")

    # 따릉이: 3분 간격, 06-23시
    scheduler.add_job(bike.run, "cron", minute="*/3", hour="6-22", id="bike_collector")

    # 신호등: 3분 간격, 06-22시
    scheduler.add_job(
        signal.run, "cron", minute="*/3", hour="6-21", id="signal_collector"
    )

    logger.info("수집 스케줄러 등록 완료: bus(2분), bike(3분), signal(3분)")
    return scheduler
