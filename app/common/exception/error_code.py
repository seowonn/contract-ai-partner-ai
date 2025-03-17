from enum import Enum
from http import HTTPStatus


class ErrorCode(Enum):
  # global 에러
  REQUEST_UNMATCH = (HTTPStatus.BAD_REQUEST, "G001", "요청 json 매핑 불일치")

  # standard 관련 에러
  UPLOAD_FAIL = (HTTPStatus.INTERNAL_SERVER_ERROR, "S001", "기준 문서 저장 과정 중 에러 발생")
  UNEXPECTED_RESPONSE = (HTTPStatus.BAD_REQUEST, "S002", "맞지 않은 형식의 요청으로 다른 결과가 나옴")

  # common 에러
  DATA_TYPE_NOT_MATCH = (HTTPStatus.BAD_REQUEST, "C001", "데이터의 형식이 맞지 않음")
  FILE_LOAD_FAILED = (HTTPStatus.BAD_REQUEST, "C002", "S3에서 파일을 가져 오지 못함")
  S3_CLIENT_ERROR = (HTTPStatus.INTERNAL_SERVER_ERROR, "C003", "S3 연결 도중 에러 발생")
  CONVERT_TO_IO_FAILED = (HTTPStatus.INTERNAL_SERVER_ERROR, "C004", "스트림을 io 바이트로 변환하는데 에러 발생")
  INNER_DATA_ERROR = (HTTPStatus.INTERNAL_SERVER_ERROR, "C005", "페이지가 없거나 내부 구조가 깨져 있음")
  FILE_FORMAT_INVALID = (HTTPStatus.INTERNAL_SERVER_ERROR, "C006", "파일이 깨졌 거나 지원 불가입니다.")

  def __init__(self, status: HTTPStatus, code: str, message: str):
    self.status = status
    self.code = code
    self.message = message
