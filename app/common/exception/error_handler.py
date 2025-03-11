from http import HTTPStatus
import logging

from pydantic import ValidationError
from app.common.exception.custom_exception import BaseCustomException
from app.schemas.error_response import ErrorResponse

logger = logging.getLogger(__name__)

def register_error_handlers(app):

  @app.errorhandler(ValidationError)
  def handle_validation_error(e: ValidationError):
    logger.debug(f"[ValidationError]: {str(e)}")
    error_code = ErrorCode.REQUEST_UNMATCH
    error_response = ErrorResponse(error_code.code, error_code.message)
    return error_response.of(), HTTPStatus.BAD_REQUEST


  @app.errorhandler(BaseCustomException)
  def handle_custom_exception(e: BaseCustomException):
    error_response = ErrorResponse(e.code, str(e))
    return error_response.of(), e.status

  @app.errorhandler(Exception)
  def handle_unexpected_exception(e: Exception):
    error_response = ErrorResponse(e.code, str(e))
    return error_response.of(), e.status