import psycopg2
import redis
from loguru import logger

from app.config import settings


def get_pg_connection():
    """PostgreSQL 연결을 반환한다."""
    try:
        conn = psycopg2.connect(settings.pg_dsn)
        return conn
    except Exception as e:
        logger.error("PostgreSQL 연결 실패: {}", e)
        raise


def get_redis():
    """Redis 클라이언트를 반환한다."""
    try:
        return redis.from_url(settings.redis_url, decode_responses=True)
    except Exception as e:
        logger.error("Redis 연결 실패: {}", e)
        raise
