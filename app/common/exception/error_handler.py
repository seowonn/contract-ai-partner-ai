from http import HTTPStatus
import traceback
import logging

from pydantic import ValidationError
from werkzeug.exceptions import NotFound

from app.blueprints.agreement.agreement_exception import AgreementException
from app.blueprints.standard.standard_exception import StandardException
from app.common.exception.custom_exception import CommonException
from app.common.exception.error_code import ErrorCode
from app.schemas.error_response import ErrorResponse

logger = logging.getLogger(__name__)

def register_error_handlers(app):

  @app.errorhandler(NotFound)
  def handle_not_found_error(e: NotFound):
    logger.error(f"[NotFound]: {str(e)}\n{traceback.format_exc()}")
    error_code = ErrorCode.URL_NOT_FOUND
    error_response = ErrorResponse(error_code.code, error_code.message)
    return error_response.of(), HTTPStatus.BAD_REQUEST

  @app.errorhandler(ValidationError)
  def handle_validation_error(e: ValidationError):
    logger.error(f"[ValidationError]: {str(e)}\n{traceback.format_exc()}")
    error_code = ErrorCode.REQUEST_UNMATCH
    error_response = ErrorResponse(error_code.code, error_code.message)
    return error_response.of(), HTTPStatus.BAD_REQUEST

  @app.errorhandler(StandardException)
  def handle_custom_exception(e: StandardException):
    logger.error(f"[StandardException]: {str(e)}\n{traceback.format_exc()}")
    error_response = ErrorResponse(e.code, str(e))
    return error_response.of(), e.status

  @app.errorhandler(AgreementException)
  def handle_custom_exception(e: AgreementException):
    logger.error(f"[AgreementException]: {str(e)}\n{traceback.format_exc()}")
    error_response = ErrorResponse(e.code, str(e))
    return error_response.of(), e.status

  @app.errorhandler(CommonException)
  def handle_custom_exception(e: CommonException):
    logger.error(f"[BaseCustomException]: {str(e)}\n{traceback.format_exc()}")
    error_response = ErrorResponse(e.code, str(e))
    return error_response.of(), e.status

  @app.errorhandler(Exception)
  def handle_unexpected_exception(e: Exception):
    logger.error(f"[Exception]: {str(e)}\n{traceback.format_exc()}")
    error_response = ErrorResponse("서버 내부 동작 오류", str(e))
    return error_response.of(), 500