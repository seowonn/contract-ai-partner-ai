import logging
from http import HTTPStatus
from typing import List

from flask import Blueprint, request
from pydantic import ValidationError

from app.blueprints.agreement.agreement_exception import AgreementException
from app.blueprints.common.async_loop import run_async
from app.common.exception.custom_exception import BaseCustomException
from app.common.exception.error_code import ErrorCode
from app.common.file_type import FileType
from app.schemas.analysis_response import AnalysisResponse
from app.schemas.chunk_schema import Document
from app.schemas.document_request import DocumentRequest
from app.schemas.success_code import SuccessCode
from app.schemas.success_response import SuccessResponse
from app.services.agreement.img_service import process_img
from app.services.agreement.vectorize_similarity import \
  vectorize_and_calculate_similarity, byte_data
from app.services.common.ingestion_pipeline import \
  combine_chunks_by_clause_number, preprocess_data2
from app.services.common.ingestion_pipeline import chunk_agreement_documents
from app.containers.service_container import prompt_service
import time

from config.app_config import AppConfig

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

  documents: List[Document] = []
  pdf_bytes_io = None
  if document_request.type in (FileType.PNG, FileType.JPG, FileType.JPEG):
    extracted_text = process_img(document_request)
  elif document_request.type == FileType.PDF:
    documents, pdf_bytes_io = preprocess_data2(document_request)
  else:
    raise AgreementException(ErrorCode.UNSUPPORTED_FILE_TYPE)

  if len(documents) == 0:
    raise AgreementException(ErrorCode.NO_TEXTS_EXTRACTED)

  summary_content = prompt_service.summarize_document(documents)

  document_chunks = chunk_agreement_documents(documents)

  combined_chunks = combine_chunks_by_clause_number(document_chunks)

  # 5️⃣ 벡터화 + 유사도 비교 (리턴값 추가)
  byte_data(pdf_bytes_io)

  start_time = time.time()
  chunks = run_async(
      vectorize_and_calculate_similarity(
          combined_chunks, AppConfig.COLLECTION_NAME, document_request))
  end_time = time.time()
  logging.info(
      f"Time vectorize and prompt texts: {end_time - start_time:.4f} seconds")

  response = AnalysisResponse(
      total_page=len(documents),
      summary_content=summary_content,
      chunks=chunks
  )

  return SuccessResponse(SuccessCode.REVIEW_SUCCESS,
                         response).of(), HTTPStatus.OK