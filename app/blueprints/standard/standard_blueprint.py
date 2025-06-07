import asyncio
import re
from http import HTTPStatus

from flask import Blueprint

from app.blueprints.agreement.agreement_exception import AgreementException
from app.common.constants import SUCCESS
from app.common.decorators import parse_request
from app.common.exception.error_code import ErrorCode
from app.schemas.analysis_response import StandardResponse
from app.schemas.document_request import DocumentRequest
from app.schemas.success_code import SuccessCode
from app.schemas.success_response import SuccessResponse
from app.services.common.ingestion_pipeline import load_pdf, \
  chunk_standard_texts
from app.services.standard.vector_delete import delete_by_standard_id
from app.services.standard.vector_store.vector_processor import \
  vectorize_and_save

standards = Blueprint('standards', __name__, url_prefix="/flask/standards")


@standards.route('/analysis', methods=['POST'])
@parse_request(DocumentRequest)
def process_standards_pdf_from_s3(document_request: DocumentRequest):

  documents, _ = load_pdf(document_request)
  chunks = chunk_standard_texts(documents, document_request.categoryName)

  asyncio.run(vectorize_and_save(chunks, document_request))

  contents = [normalize_spacing(doc.page_content) for doc in documents]
  return SuccessResponse(SuccessCode.ANALYSIS_COMPLETE,
                         StandardResponse(result=SUCCESS, contents=contents)).of(), HTTPStatus.OK


@standards.route('<categoryName>/<standardId>', methods=["DELETE"])
def delete_standard(categoryName: str, standardId: str):
  if not categoryName.strip() or not standardId.strip():
    raise AgreementException(ErrorCode.INVALID_URL_PARAMETER)

  if not standardId.isdigit():
    raise AgreementException(ErrorCode.CANNOT_CONVERT_TO_NUM)

  success_code = (
    asyncio.run(delete_by_standard_id(int(standardId), categoryName)))
  return SuccessResponse(success_code, SUCCESS).of(), HTTPStatus.OK


def normalize_spacing(text: str) -> str:
  text = text.replace('\n', '[[[NEWLINE]]]')
  text = re.sub(r'\s{5,}', '\n', text)
  text = text.replace('[[[NEWLINE]]]', '\n')
  return text
