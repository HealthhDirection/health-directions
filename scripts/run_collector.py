"""수집기 실행 진입점.

별도 프로세스로 실행: python scripts/run_collector.py
"""

import sys
from pathlib import Path

# 프로젝트 루트를 PYTHONPATH에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from loguru import logger

from app.collectors.scheduler import create_scheduler


def main():
    logger.info("수집기 시작")
    scheduler = create_scheduler()
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("수집기 종료")


if __name__ == "__main__":
    main()
