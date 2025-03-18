from http import HTTPStatus
from flask import Blueprint, request

from app.blueprints.agreement.agreement_exception import AgreementException
from app.common.exception.custom_exception import BaseCustomException
from app.common.file_type import FileType
from app.schemas.pdf_request import AgreementPDFRequest
from app.schemas.success_code import SuccessCode
from app.schemas.success_response import SuccessResponse
from app.services.agreement import processor
from pydantic import ValidationError


agreements = Blueprint('agreements', __name__, url_prefix="/flask/agreements")

@agreements.route('/', methods=['POST'])
def process_agreement_pdf_from_s3():
  # return 예외방지
  data = None

  try:
    pdf_request = AgreementPDFRequest(**request.get_json())
  except ValidationError as e:
    raise e

  status_code = HTTPStatus.OK
  try:
    if (pdf_request.type == FileType.PDF):
      data, status_code = processor.process_pdf(pdf_request)
  except (AgreementException, BaseCustomException) as e:
    raise e
  except Exception as e:
    raise e

  return SuccessResponse(SuccessCode.REVIEW_SUCCESS, data).of(), status_code
