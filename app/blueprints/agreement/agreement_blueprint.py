import asyncio
import logging
from http import HTTPStatus

from flask import Blueprint, request
from pydantic import ValidationError

from app.blueprints.agreement.agreement_exception import AgreementException
from app.common.exception.custom_exception import BaseCustomException
from app.common.exception.error_code import ErrorCode
from app.common.file_type import FileType
from app.schemas.document_request import DocumentRequest
from app.schemas.success_code import SuccessCode
from app.schemas.success_response import SuccessResponse
from app.services.agreement.img_service import process_img
from app.services.agreement.vectorize_similarity import \
  vectorize_and_calculate_similarity
from app.services.common.processor import preprocess_data, chunk_texts
import time

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

  if document_request.type in (FileType.PNG, FileType.JPG, FileType.JPEG):
    extracted_text = process_img(document_request)
  elif document_request.type == FileType.PDF:
    extracted_text = preprocess_data(document_request)
  else:
    raise AgreementException(ErrorCode.UNSUPPORTED_FILE_TYPE)

  if not extracted_text:
    raise AgreementException(ErrorCode.NO_TEXTS_EXTRACTED)

  chunks = chunk_texts(extracted_text)

  # 5️⃣ 벡터화 + 유사도 비교 (리턴값 추가)
  start_time = time.time()
  result = asyncio.run(vectorize_and_calculate_similarity(extracted_text, chunks, document_request))
  end_time = time.time()
  print(f"Time vectorize and prompt texts: {end_time - start_time:.4f} seconds")
  logging.info(f"Time vectorize and prompt texts: {end_time - start_time:.4f} seconds")

  return SuccessResponse(SuccessCode.REVIEW_SUCCESS, result).of(), HTTPStatus.OK
