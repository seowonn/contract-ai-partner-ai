import os
from typing import Tuple

from dotenv import load_dotenv

from app.blueprints.agreement.agreement_exception import AgreementException
from app.common.exception.error_code import ErrorCode

load_dotenv()


def get_naver_ocr_client() -> Tuple[str, dict]:
  api_url = os.getenv("NAVER_CLOVA_API_URL")
  api_key = os.getenv("NAVER_CLOVA_API_KEY")

  if not api_url or not api_key:
    raise AgreementException(ErrorCode.NAVER_OCR_SETTING_LOAD_FAIL)

  headers = {
    "X-OCR-SECRET": api_key
  }
  return api_url, headers