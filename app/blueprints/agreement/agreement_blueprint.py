from http import HTTPStatus

from flask import Blueprint, request
from pydantic import ValidationError

from app.common.exception.custom_exception import CommonException
from app.common.exception.error_code import ErrorCode
from app.common.file_type import FileType
from app.schemas.analysis_response import AnalysisResponse
from app.schemas.document_request import DocumentRequest
from app.schemas.success_code import SuccessCode
from app.schemas.success_response import SuccessResponse
from app.services.common.ingestion_pipeline import \
  extract_file_type, \
  pdf_agreement_service, ocr_service

agreements = Blueprint('agreements', __name__, url_prefix="/flask/agreements")


@agreements.route('/analysis', methods=['POST'])
def process_agreements_pdf_from_s3():
  try:
    json_data = request.get_json()
    if json_data is None:
      raise CommonException(ErrorCode.INVALID_JSON_FORMAT)

    document_request = DocumentRequest(**json_data)
  except ValidationError:
    raise CommonException(ErrorCode.FIELD_MISSING)

  file_type = extract_file_type(document_request.url)
  if file_type in (FileType.PNG, FileType.JPG, FileType.JPEG):
    chunks, total_chunks, total_page = ocr_service(document_request)
  elif file_type == FileType.PDF:
    chunks, total_chunks, total_page = pdf_agreement_service(document_request)
  else:
    raise CommonException(ErrorCode.UNSUPPORTED_FILE_TYPE)

  return SuccessResponse(SuccessCode.REVIEW_SUCCESS,
                         AnalysisResponse(total_page=total_page,
                                          chunks=chunks,
                                          total_chunks=total_chunks)
                         ).of(), HTTPStatus.OK
