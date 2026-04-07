from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PostgreSQL
    pg_dsn: str = "postgresql://postgres:password@localhost:5433/gangseo_transit"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # 공공데이터포털 API 키
    bus_api_key: str = ""
    bike_api_key: str = ""
    signal_api_key: str = ""

    # TMAP
    tmap_app_key: str = ""

    # 강서구 바운딩박스
    gangseo_lat_min: float = 37.53
    gangseo_lat_max: float = 37.58
    gangseo_lng_min: float = 126.80
    gangseo_lng_max: float = 126.88

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
