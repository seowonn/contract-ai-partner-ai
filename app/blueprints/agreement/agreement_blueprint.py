from http import HTTPStatus

from flask import Blueprint

from app.blueprints.agreement.agreement_exception import AgreementException
from app.common.decorators import parse_request
from app.common.exception.error_code import ErrorCode
from app.common.file_type import FileType
from app.schemas.analysis_response import AnalysisResponse, \
  DocumentAnalysisResult
from app.schemas.document_request import DocumentRequest
from app.schemas.success_code import SuccessCode
from app.schemas.success_response import SuccessResponse
from app.services.common.ingestion_pipeline import extract_file_type, \
  pdf_agreement_service, ocr_service

agreements = Blueprint('agreements', __name__, url_prefix="/flask/agreements")
IMAGE_FILE_TYPES = (FileType.PNG, FileType.JPG, FileType.JPEG)


@agreements.route('/analysis', methods=['POST'])
@parse_request(DocumentRequest)
def process_uploaded_agreement(document_request: DocumentRequest):
  file_type = extract_file_type(document_request.url)
  if file_type in IMAGE_FILE_TYPES:
    result: DocumentAnalysisResult = ocr_service(document_request)
  elif file_type == FileType.PDF:
    result: DocumentAnalysisResult = pdf_agreement_service(document_request)
  else:
    raise AgreementException(ErrorCode.UNSUPPORTED_FILE_TYPE)

  return SuccessResponse(SuccessCode.REVIEW_SUCCESS,
                         AnalysisResponse(chunks=result.chunks,
                                          total_chunks=result.total_chunks,
                                          total_page=result.total_pages)
                         ).of(), HTTPStatus.OK
