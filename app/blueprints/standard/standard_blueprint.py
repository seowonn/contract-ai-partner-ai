from http import HTTPStatus

from flask import Blueprint, request

from app.blueprints.standard.standard_exception import StandardException
from app.common.exception.custom_exception import BaseCustomException
from app.common.file_type import FileType
from app.schemas.document_request import DocumentRequest
from app.schemas.success_code import SuccessCode
from app.schemas.success_response import SuccessResponse
from app.services.standard import processor
from pydantic import ValidationError

from app.services.standard.vector_delete import delete_by_standard_id

standards = Blueprint('standards', __name__, url_prefix="/flask/standards")

@standards.route('', methods=['POST'])
def process_pdf_from_s3():

  try:
    document_request = DocumentRequest(**request.get_json())
  except ValidationError as e:
    raise e

  status_code = HTTPStatus.OK
  try:
    if document_request.type == FileType.PDF:
      status_code = processor.process_pdf(document_request)
  except Exception as e:
    raise e

  return SuccessResponse(SuccessCode.UPLOAD_SUCCESS, "success").of(), status_code


@standard.route('/<standardId>', methods=["DELETE"])
def delete_standard(standardId: str):
  status_code = delete_by_standard_id(int(standardId))
  return SuccessResponse(SuccessCode.DELETE_SUCCESS, "success").of(), status_code