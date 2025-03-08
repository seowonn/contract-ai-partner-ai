from enum import Enum
from http import HTTPStatus


class ErrorCode(Enum):
  # standard 관련 에러
  REQUEST_NOT_MATCH = (HTTPStatus.BAD_REQUEST, "S001", "전달받은 인자를 매핑할 수 없음")
  S3FILE_NOT_FOUND = (HTTPStatus.BAD_REQUEST, "S002", "S3에서 파일을 찾을 수 없음")
  UPLOAD_FAIL = (HTTPStatus.INTERNAL_SERVER_ERROR, "S003", "기준문서 저장 과정 중 에러 발생")

  # common 에러
  DATA_TYPE_NOT_MATCH = (HTTPStatus.BAD_REQUEST, "C001", "데이터의 형식이 맞지 않음")


  def __init__(self, status: HTTPStatus, code: str, message: str):
    self.status = status
    self.code = code
    self.message = message
