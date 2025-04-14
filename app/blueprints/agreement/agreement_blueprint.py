import asyncio
import logging
from http import HTTPStatus

from flask import Blueprint, request
from pydantic import ValidationError

from app.common.exception.custom_exception import CommonException
from app.common.exception.error_code import ErrorCode
from app.schemas.analysis_response import AnalysisResponse
from app.schemas.document_request import DocumentRequest
from app.schemas.success_code import SuccessCode
from app.schemas.success_response import SuccessResponse
from app.services.agreement.vectorize_similarity import \
  vectorize_and_calculate_similarity, vectorize_and_calculate_similarity_ocr
from app.services.common.ingestion_pipeline import \
  combine_chunks_by_clause_number, preprocess_data, preprocess_data_ocr, combine_chunks_by_clause_number_ocr
from app.services.common.ingestion_pipeline import chunk_agreement_documents, chunk_agreement_documents_ocr
import time

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

  # documents, fitz_document = preprocess_data(document_request)
  documents, all_texts_with_bounding_boxes = preprocess_data_ocr(document_request)

  # document_chunks = chunk_agreement_documents(documents)
  document_chunks = chunk_agreement_documents_ocr(documents)

  # combined_chunks = combine_chunks_by_clause_number(document_chunks)
  combined_chunks = combine_chunks_by_clause_number_ocr(document_chunks)

  start_time = time.time()
  # chunks = asyncio.run(
  #     vectorize_and_calculate_similarity(combined_chunks, document_request,
  #                                        fitz_document))
  chunks = asyncio.run(
      vectorize_and_calculate_similarity_ocr(combined_chunks, document_request,
                                         all_texts_with_bounding_boxes))
  end_time = time.time()
  logging.info(
      f"Time vectorize and prompt texts: {end_time - start_time:.4f} seconds")

  return SuccessResponse(SuccessCode.REVIEW_SUCCESS,
                         AnalysisResponse(total_page=len(documents),
                                          chunks=chunks,
                                          total_chunks=len(combined_chunks))
                         ).of(), HTTPStatus.OK
