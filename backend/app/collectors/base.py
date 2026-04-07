"""수집기 베이스 클래스. 재시도, 로깅, 속도 제한 공통 로직."""

import abc
import time

import httpx
from loguru import logger


class BaseCollector(abc.ABC):
    """모든 수집기가 상속하는 추상 클래스."""

    name: str = "base"
    max_retries: int = 3
    retry_delay: float = 2.0  # 초

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.Client(timeout=10.0)

    @abc.abstractmethod
    def collect(self) -> int:
        """데이터를 수집하고 저장된 레코드 수를 반환한다."""
        ...

    def call_api(self, url: str, params: dict | None = None) -> httpx.Response:
        """API 호출 + 재시도 로직."""
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.client.get(url, params=params)
                resp.raise_for_status()
                return resp
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                logger.warning(
                    f"[{self.name}] API 호출 실패 (시도 {attempt}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)
                else:
                    raise

    def run(self):
        """수집 실행 + 로깅."""
        start = time.time()
        try:
            count = self.collect()
            duration_ms = int((time.time() - start) * 1000)
            logger.info(f"[{self.name}] 수집 완료: {count}건 ({duration_ms}ms)")
            return {"status": "SUCCESS", "count": count, "duration_ms": duration_ms}
        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            logger.error(f"[{self.name}] 수집 실패: {e}")
            return {
                "status": "FAIL",
                "count": 0,
                "duration_ms": duration_ms,
                "error": str(e),
            }

    def close(self):
        self.client.close()
