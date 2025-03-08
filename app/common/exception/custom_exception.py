from app.common.exception.error_code import ErrorCode


class BaseCustomException(Exception):

  def __init__(self, error: ErrorCode):
    super().__init__(error.message)
    self.status = error.status
    self.code = error.code
