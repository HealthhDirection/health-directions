"""서울시 버스정류소 엑셀 파일을 master.bus_stops에 적재한다.

실행: python scripts/import_bus_stops_excel.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import pandas as pd
from loguru import logger
from app.config import settings
from app.db.connection import get_pg_connection

EXCEL_PATH = Path(__file__).resolve().parent.parent / "서울시버스정류소위치정보(20260108).xlsx"

GANGSEO_LAT_MIN, GANGSEO_LAT_MAX = 37.53, 37.58
GANGSEO_LNG_MIN, GANGSEO_LNG_MAX = 126.80, 126.88


def main():
    logger.info("엑셀 파일 읽는 중: {}", EXCEL_PATH)
    df = pd.read_excel(EXCEL_PATH)

    # 컬럼 이름 정리 (인코딩 무관하게 위치로 접근)
    df.columns = ["stop_id", "ars_id", "stop_name", "longitude", "latitude", "bus_type"]

    # 숫자 변환
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df = df.dropna(subset=["latitude", "longitude"])

    # 강서구 범위 필터링
    mask = (
        (df["latitude"] >= GANGSEO_LAT_MIN) & (df["latitude"] <= GANGSEO_LAT_MAX) &
        (df["longitude"] >= GANGSEO_LNG_MIN) & (df["longitude"] <= GANGSEO_LNG_MAX)
    )
    df = df[mask].copy()
    logger.info("강서구 범위 정류장: {}개", len(df))

    if df.empty:
        logger.warning("필터링 결과 없음. 좌표 범위 확인 필요.")
        return

    records = [
        {
            "stop_id": str(row["stop_id"]),
            "stop_name": str(row["stop_name"]),
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
        }
        for _, row in df.iterrows()
    ]

    sql = """
        INSERT INTO master.bus_stops (stop_id, stop_name, latitude, longitude)
        VALUES (%(stop_id)s, %(stop_name)s, %(latitude)s, %(longitude)s)
        ON CONFLICT (stop_id) DO UPDATE SET
            stop_name  = EXCLUDED.stop_name,
            latitude   = EXCLUDED.latitude,
            longitude  = EXCLUDED.longitude,
            updated_at = now()
    """

    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, records)
        conn.commit()
        logger.info("버스 정류장 {}건 UPSERT 완료", len(records))
    except Exception as e:
        conn.rollback()
        logger.error("DB 저장 실패: {}", e)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
