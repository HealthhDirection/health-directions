import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api import routes, signals, stations, status
from app.config import settings
from app.utils.logging import setup_logging

# 서버 기동 직후 로깅 초기화 (uvicorn import 전에 설정)
setup_logging(log_level=settings.log_level, log_dir=settings.log_dir)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("건강길찾기 API 시작 (v{})", app.version)
    logger.info(
        "설정: PG={}, Redis={}, TMAP={}, BUS={}, BIKE={}, SIGNAL={}",
        bool(settings.pg_dsn),
        bool(settings.redis_url),
        bool(settings.tmap_app_key),
        bool(settings.bus_api_key),
        bool(settings.bike_api_key),
        bool(settings.signal_api_key),
    )
    yield
    logger.info("건강길찾기 API 종료")


app = FastAPI(
    title="건강길찾기 API (Health Directions)",
    description=(
        "버스·따릉이·신호등 실시간 데이터 기반 경로 추천\n\n"
        "## 환경 변수 설정 (`backend/.env`)\n\n"
        "| 변수명 | 용도 |\n"
        "|--------|------|\n"
        "| `SIGNAL_API_KEY` | 공공데이터포털 — RTI 신호등 API 키 |\n"
        "| `BUS_API_KEY` | 공공데이터포털 — 서울 버스 API 키 |\n"
        "| `BIKE_API_KEY` | 서울 열린데이터광장 — 따릉이 API 키 |\n"
        "| `TMAP_APP_KEY` | SK TMAP — 경로 탐색 API 키 |\n\n"
        "외부 API를 호출하는 엔드포인트(`/api/signals/live` 등)는 "
        "Swagger에서 `api_key` 파라미터에 키를 직접 입력하여 테스트할 수 있습니다."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """모든 HTTP 요청/응답을 로깅한다."""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = int((time.perf_counter() - start) * 1000)

    level = "WARNING" if response.status_code >= 400 else "INFO"
    logger.log(
        level,
        "{} {} → {} ({}ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router, prefix="/api")
app.include_router(stations.router, prefix="/api")
app.include_router(status.router, prefix="/api")
app.include_router(signals.router)


@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok"}


@app.get("/config/check", tags=["system"], summary="환경 변수 설정 확인")
def config_check():
    """서버에 설정된 API 키 현황을 반환한다. (값 자체는 노출하지 않음)"""
    return {
        "SIGNAL_API_KEY": bool(settings.signal_api_key),
        "BUS_API_KEY": bool(settings.bus_api_key),
        "BIKE_API_KEY": bool(settings.bike_api_key),
        "TMAP_APP_KEY": bool(settings.tmap_app_key),
        "PG_DSN": settings.pg_dsn.split("@")[-1] if settings.pg_dsn else None,
        "REDIS_URL": settings.redis_url,
    }
