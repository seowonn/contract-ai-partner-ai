from enum import Enum
from http import HTTPStatus


class SuccessCode(Enum):
  ANALYSIS_COMPLETE = (HTTPStatus.OK, "S001", "기준 문서 AI 분석 완료")
  DELETE_SUCCESS = (HTTPStatus.OK, "S002", "문서 삭제 완료")
  NO_DOCUMENT_FOUND = (HTTPStatus.OK, "S003", "발견된 기준 문서 없음")

  REVIEW_SUCCESS = (HTTPStatus.OK, "A001", "계약서 검토 완료")


  def __init__(self, status: HTTPStatus, code: str, message: str):
    self.status = status
    self.code = code
    self.message = message
