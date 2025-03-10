from app.common.exception.custom_exception import BaseCustomException
from app.schemas.error_response import ErrorResponse


def register_error_handlers(app):

  @app.errorhandler(BaseCustomException)
  def handle_custom_exception(e: BaseCustomException):
    error_response = ErrorResponse(e.code, str(e))
    return error_response.of(), e.status

  @app.errorhandler(Exception)
  def handle_unexpected_exception(e: Exception):
    error_response = ErrorResponse(e.code, str(e))
    return error_response.of(), e.status