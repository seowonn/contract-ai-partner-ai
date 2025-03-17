from enum import Enum
from http import HTTPStatus


class SuccessCode(Enum):
  UPLOAD_SUCCESS = (HTTPStatus.OK, "S001", "문서 업로드 완료")
  DELETE_SUCCESS = (HTTPStatus.OK, "S002", "문서 삭제 완료")


  def __init__(self, status: HTTPStatus, code: str, message: str):
    self.status = status
    self.code = code
    self.message = message
