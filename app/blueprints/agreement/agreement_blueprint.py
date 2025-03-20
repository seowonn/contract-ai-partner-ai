from http import HTTPStatus

from flask import Blueprint, request
from pydantic import ValidationError

from app.common.exception.custom_exception import BaseCustomException
from app.common.exception.error_code import ErrorCode
from app.common.file_type import FileType
from app.schemas.document_request import DocumentRequest
from app.schemas.success_code import SuccessCode
from app.schemas.success_response import SuccessResponse
from app.services.agreement.img_service import process_img
from app.services.agreement.vectorize_similarity import vectorize_and_calculate_similarity
from app.services.common.processor import preprocess_data

agreements = Blueprint('agreements', __name__, url_prefix="/flask/agreements")

@agreements.route('/analysis', methods=['POST'])
def process_agreements_pdf_from_s3():
  try:
    json_data = request.get_json()
    if json_data is None:
      raise BaseCustomException(ErrorCode.INVALID_JSON_FORMAT)

    document_request = DocumentRequest(**json_data)
  except ValidationError:
    raise BaseCustomException(ErrorCode.FIELD_MISSING)

  status_code = HTTPStatus.OK
  try:
    if document_request.type in (FileType.PNG, FileType.JPG, FileType.JPEG):
      extracted_text = process_img(document_request)
    elif document_request.type == FileType.PDF:
      chunks = preprocess_data(document_request)

      # 5️⃣ 벡터화 + 유사도 비교 (리턴값 추가)
      result, status_code = vectorize_and_calculate_similarity(chunks, document_request)
    else:
      pass
  except Exception as e:
    raise e

  return SuccessResponse(SuccessCode.REVIEW_SUCCESS, result).of(), status_code
