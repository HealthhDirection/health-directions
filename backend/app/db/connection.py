import psycopg2
import redis

from app.config import settings


def get_pg_connection():
    """PostgreSQL 연결을 반환한다."""
    return psycopg2.connect(settings.pg_dsn)


def get_redis():
    """Redis 클라이언트를 반환한다."""
    return redis.from_url(settings.redis_url, decode_responses=True)
