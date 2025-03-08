from app.common.exception.custom_exception import BaseCustomException
from app.common.exception.error_response import ErrorResponse


def register_error_handlers(app):

  @app.errorhandler(BaseCustomException)
  def handle_custom_exception(e: BaseCustomException):
    return ErrorResponse.of(e.code, str(e)), e.status
