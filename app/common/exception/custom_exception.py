from app.common.exception.error_code import ErrorCode


class BaseCustomException(Exception):

  def __init__(self, error_code: ErrorCode):
    super().__init__(error_code.message)
    self.status = error_code.status
    self.code = error_code.code
