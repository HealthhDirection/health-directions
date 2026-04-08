"""중앙 로깅 설정 — loguru 기반.

uvicorn / 표준 logging 출력을 loguru로 리다이렉트하고
파일 로테이션을 설정한다.
"""

import logging
import sys
from pathlib import Path

from loguru import logger


class _InterceptHandler(logging.Handler):
    """표준 logging → loguru 리다이렉트 핸들러."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


_LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{line}</cyan> — "
    "<level>{message}</level>"
)


def setup_logging(log_level: str = "INFO", log_dir: str = "logs") -> None:
    """loguru 설정 초기화.

    - stderr: 컬러 포맷
    - 파일: logs/app.log (10 MB 로테이션, 30일 보관)
    - uvicorn 표준 logging → loguru 리다이렉트
    """
    logger.remove()

    # stderr 컬러 출력
    logger.add(sys.stderr, level=log_level, format=_LOG_FORMAT, colorize=True)

    # 파일 로테이션 (10 MB, 30일 보관)
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    logger.add(
        Path(log_dir) / "app.log",
        level=log_level,
        format=_LOG_FORMAT,
        rotation="10 MB",
        retention="30 days",
        encoding="utf-8",
    )

    # uvicorn / 표준 logging → loguru 리다이렉트
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        log = logging.getLogger(name)
        log.handlers = [_InterceptHandler()]
        log.propagate = False

    logger.info("로깅 초기화 완료: level={}, log_dir={}", log_level, log_dir)
