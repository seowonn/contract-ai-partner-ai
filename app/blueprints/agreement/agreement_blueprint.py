from http import HTTPStatus

from flask import Blueprint, request
from pydantic import ValidationError

from app.common.file_type import FileType
from app.schemas.document_request import DocumentRequest
from app.schemas.success_code import SuccessCode
from app.schemas.success_response import SuccessResponse
from app.services.standard import processor

agreements = Blueprint('agreements', __name__, url_prefix="/flask/agreements")

@agreements.route('', methods=['POST'])
def process_agreement_pdf_from_s3():

  try:
    document_request = DocumentRequest(**request.get_json())
  except ValidationError as e:
    raise e

  status_code = HTTPStatus.OK
  try:
    if (document_request.type == FileType.PNG or document_request.type == FileType.JPG or
        document_request.type == FileType.JPEG):
      status_code = processor.process_img(document_request)
    elif document_request.type == FileType.PDF:
      status_code = processor.process_pdf(document_request)
    else:
      pass
  except Exception as e:
    raise e

  return SuccessResponse(SuccessCode.REVIEW_SUCCESS, "success").of(), status_code
