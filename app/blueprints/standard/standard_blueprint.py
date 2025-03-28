import logging
import time
from http import HTTPStatus

from flask import Blueprint, request
from pydantic import ValidationError

from app.blueprints.agreement.agreement_exception import AgreementException
from app.blueprints.common.async_loop import run_async
from app.common.constants import SUCCESS
from app.common.exception.custom_exception import BaseCustomException
from app.common.exception.error_code import ErrorCode
from app.common.file_type import FileType
from app.schemas.document_request import DocumentRequest
from app.schemas.success_code import SuccessCode
from app.schemas.success_response import SuccessResponse
from app.services.common.ingestion_pipeline import preprocess_data, \
  chunk_standard_texts
from app.services.standard.vector_delete import delete_by_standard_id
from app.services.standard.vector_store import vectorize_and_save
from config.app_config import AppConfig

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
      documents = preprocess_data(document_request)
      extracted_text = "\n".join([doc.page_content for doc in documents])

      chunks = chunk_standard_texts(extracted_text)

      # 5️⃣ 벡터화 + Qdrant 저장
      start_time = time.time()
      run_async(vectorize_and_save(
          chunks, AppConfig.COLLECTION_NAME, document_request))
      end_time = time.time()
      logging.info(f"vectorize_and_save 소요 시간: {end_time - start_time}")

  except Exception as e:
    raise e

  return SuccessResponse(SuccessCode.ANALYSIS_COMPLETE,
                         SUCCESS).of(), status_code


@standards.route('/<standardId>', methods=["DELETE"])
def delete_standard(standardId: str):
  if not standardId.strip():
    raise AgreementException(ErrorCode.INVALID_URL_PARAMETER)

  if not standardId.isdigit():
    raise AgreementException(ErrorCode.CANNOT_CONVERT_TO_NUM)

  run_async(delete_by_standard_id(int(standardId), AppConfig.COLLECTION_NAME))
  return SuccessResponse(SuccessCode.DELETE_SUCCESS,
                         SUCCESS.value).of(), HTTPStatus.OK
