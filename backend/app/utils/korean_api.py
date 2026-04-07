"""data.go.kr 공공데이터 OpenAPI 공통 래퍼.

XML/JSON 응답 파싱, 인코딩 자동 감지, 에러코드 매핑.
"""

import httpx
from loguru import logger
from lxml import etree


class KoreanApiError(Exception):
    """공공데이터 API 에러."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# data.go.kr 공통 에러 코드
ERROR_CODES = {
    "00": "정상",
    "01": "애플리케이션 에러",
    "02": "DB 에러",
    "03": "데이터 없음",
    "04": "HTTP 에러",
    "05": "서비스 연결 실패",
    "10": "잘못된 요청 파라미터",
    "11": "필수 파라미터 누락",
    "12": "해당 서비스 없음",
    "20": "서비스 접근 거부",
    "22": "서비스 요청 제한 초과",
    "30": "등록되지 않은 서비스키",
    "31": "서비스키 만료",
    "32": "IP 차단",
}


def parse_xml_response(content: bytes) -> etree._Element:
    """XML 응답을 파싱한다. 인코딩 자동 감지."""
    try:
        root = etree.fromstring(content)
    except etree.XMLSyntaxError:
        # EUC-KR 인코딩 시도
        text = content.decode("euc-kr", errors="replace")
        root = etree.fromstring(text.encode("utf-8"))

    # 에러 코드 확인
    result_code = root.findtext(".//resultCode") or root.findtext(
        ".//RESULT/CODE"
    )
    if result_code and result_code != "00" and result_code != "INFO-000":
        result_msg = (
            root.findtext(".//resultMsg")
            or root.findtext(".//RESULT/MESSAGE")
            or ERROR_CODES.get(result_code, "알 수 없는 에러")
        )
        raise KoreanApiError(result_code, result_msg)

    return root


def parse_json_response(resp: httpx.Response) -> dict:
    """JSON 응답을 파싱한다."""
    data = resp.json()

    # 서울 열린데이터 광장 형식 에러 체크
    if isinstance(data, dict):
        result = data.get("RESULT") or data.get("result")
        if isinstance(result, dict):
            code = result.get("CODE") or result.get("code")
            if code and code not in ("INFO-000", "00"):
                msg = result.get("MESSAGE") or result.get("message") or ""
                raise KoreanApiError(code, msg)

    return data
