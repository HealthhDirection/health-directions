"""수집기 1회 즉시 실행 + Redis 확인 스크립트.

사용법:
    python scripts/test_collectors.py

수행 내용:
    1. Redis 연결 확인
    2. 따릉이 / 신호등 수집기 즉시 1회 실행
    3. Redis에 저장된 키 목록 + 샘플 데이터 출력
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from loguru import logger

from app.config import settings
from app.db.connection import get_pg_connection, get_redis
from app.collectors.bike_collector import BikeCollector
from app.collectors.signal_collector import SignalCollector


def check_redis(redis_client) -> bool:
    """Redis 연결 확인."""
    try:
        redis_client.ping()
        logger.info("✅ Redis 연결 성공")
        return True
    except Exception as e:
        logger.error(f"❌ Redis 연결 실패: {e}")
        logger.error("   → docker compose up -d 로 Redis를 먼저 실행하세요")
        return False


def show_redis_keys(redis_client, pattern: str, label: str, sample_count: int = 3):
    """Redis 키 목록과 샘플 데이터를 출력한다."""
    keys = redis_client.keys(pattern)
    logger.info(f"\n[{label}] 저장된 키: {len(keys)}개")

    for key in keys[:sample_count]:
        raw = redis_client.get(key)
        if raw:
            try:
                data = json.loads(raw)
                ttl = redis_client.ttl(key)
                logger.info(f"  키: {key}  (TTL: {ttl}초)")
                # 주요 필드만 출력
                if "available_bikes" in data:
                    logger.info(f"    available_bikes={data['available_bikes']}, station_name={data.get('station_name', '')}")
                elif "crsrdId" in data:
                    logger.info(f"    crsrdId={data['crsrdId']}, intersection_name={data.get('crsrdNm', '')}")
                else:
                    preview = str(data)[:120]
                    logger.info(f"    {preview}")
            except Exception:
                logger.info(f"  키: {key} → (파싱 불가) {raw[:80]}")

    if len(keys) > sample_count:
        logger.info(f"  ... 외 {len(keys) - sample_count}개")


def main():
    logger.info("=" * 60)
    logger.info("수집기 테스트 시작")
    logger.info("=" * 60)

    # 1. Redis 연결
    redis_client = get_redis()
    if not check_redis(redis_client):
        sys.exit(1)

    # 2. DB 연결
    try:
        pg_conn = get_pg_connection()
        logger.info("✅ PostgreSQL 연결 성공")
    except Exception as e:
        logger.error(f"❌ PostgreSQL 연결 실패: {e}")
        sys.exit(1)

    # 3. 따릉이 수집기 실행
    logger.info("\n" + "-" * 40)
    logger.info("🚲 따릉이 수집기 실행 중...")
    bike = BikeCollector(
        api_key=settings.bike_api_key,
        pg_conn=pg_conn,
        redis_client=redis_client,
    )
    bike_result = bike.run()
    logger.info(f"따릉이 결과: {bike_result}")

    # 4. 신호등 수집기 실행
    logger.info("\n" + "-" * 40)
    logger.info("🚦 신호등 수집기 실행 중... (시간이 걸릴 수 있음)")
    signal = SignalCollector(
        api_key=settings.signal_api_key,
        pg_conn=pg_conn,
        redis_client=redis_client,
    )
    signal_result = signal.run()
    logger.info(f"신호등 결과: {signal_result}")

    # 5. Redis 저장 확인
    logger.info("\n" + "=" * 60)
    logger.info("📦 Redis 저장 현황")
    logger.info("=" * 60)
    show_redis_keys(redis_client, "bike:avail:*", "따릉이 가용성", sample_count=3)
    show_redis_keys(redis_client, "signal:*", "신호등", sample_count=3)

    # 6. 전체 키 수 요약
    total_bike = len(redis_client.keys("bike:avail:*"))
    total_signal = len(redis_client.keys("signal:*"))
    logger.info("\n📊 최종 요약")
    logger.info(f"  bike:avail:*  → {total_bike}개")
    logger.info(f"  signal:*      → {total_signal}개")

    # 정리
    bike.close()
    signal.close()
    pg_conn.close()
    logger.info("\n✅ 테스트 완료")


if __name__ == "__main__":
    main()
