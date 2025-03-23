import asyncio
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
from app.services.common.processor import preprocess_data, chunk_texts
from app.services.standard.vector_delete import delete_by_standard_id
from app.services.standard.vector_store import vectorize_and_save, \
  vectorize_and_save_async_with_to_thread, vectorize_and_save_by_async_gpt

import time

standards = Blueprint('standards', __name__, url_prefix="/flask/standards")

@standards.route('/analysis', methods=['POST'])
def process_standards_pdf_from_s3():
  try:
    json_data = request.get_json()
    if json_data is None:
      raise BaseCustomException(ErrorCode.INVALID_JSON_FORMAT)

    document_request = DocumentRequest(**json_data)
  except ValidationError:
    raise BaseCustomException(ErrorCode.FIELD_MISSING)

  status_code = HTTPStatus.OK
  try:
    if document_request.type == FileType.PDF:
      extracted_text = preprocess_data(document_request)
      chunks = chunk_texts(extracted_text)

      # 5️⃣ 벡터화 + Qdrant 저장
      start_time = time.time()
      vectorize_and_save(chunks, "standard1", document_request)
      end_time = time.time()
      print(f"vectorize_and_save 소요 시간: {end_time - start_time}초")

      start_time = time.time()
      asyncio.run(vectorize_and_save_async_with_to_thread(chunks, "standard2",
                                                          document_request))
      end_time = time.time()
      print(f"vectorize_and_save_async_with_to_thread 소요 시간: {end_time - start_time}초")

      start_time = time.time()
      asyncio.run(
        vectorize_and_save_by_async_gpt(chunks, "standard3", document_request))
      end_time = time.time()
      print(f"vectorize_and_save_by_async_gpt 소요 시간: {end_time - start_time}초")

  except Exception as e:
    raise e

  return SuccessResponse(SuccessCode.ANALYSIS_COMPLETE, "success").of(), status_code


@standards.route('/<standardId>', methods=["DELETE"])
def delete_standard(standardId: str):
  if not standardId.strip():
    raise AgreementException(ErrorCode.INVALID_URL_PARAMETER)

  if not standardId.isdigit():
    raise AgreementException(ErrorCode.CANNOT_CONVERT_TO_NUM)

  success_code = delete_by_standard_id(int(standardId))
  return SuccessResponse(success_code, "success").of(), HTTPStatus.OK