import asyncio
from http import HTTPStatus

from flask import Blueprint

from app.common.decorators import parse_request
from app.schemas.analysis_response import AnalysisResponse
from app.schemas.document_request import DocumentRequest
from app.schemas.success_code import SuccessCode
from app.schemas.success_response import SuccessResponse
from app.services.agreement.vectorize_similarity import \
  vectorize_and_calculate_similarity
from app.services.common.ingestion_pipeline import chunk_agreement_documents
from app.services.common.ingestion_pipeline import \
  combine_chunks_by_clause_number, preprocess_data

agreements = Blueprint('agreements', __name__, url_prefix="/flask/agreements")


@agreements.route('/analysis', methods=['POST'])
@parse_request(DocumentRequest)
def process_agreements_pdf_from_s3(document_request: DocumentRequest):
  documents, fitz_document = preprocess_data(document_request)
  document_chunks = chunk_agreement_documents(documents)
  combined_chunks = combine_chunks_by_clause_number(document_chunks)

  chunks = asyncio.run(
    vectorize_and_calculate_similarity(combined_chunks, document_request,
                                       fitz_document))

  return SuccessResponse(SuccessCode.REVIEW_SUCCESS,
                         AnalysisResponse(total_page=len(documents),
                                          chunks=chunks,
                                          total_chunks=len(combined_chunks))
                         ).of(), HTTPStatus.OK
