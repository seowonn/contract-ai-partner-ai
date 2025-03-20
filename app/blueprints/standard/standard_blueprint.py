from http import HTTPStatus

from flask import Blueprint, request
from pydantic import ValidationError

from app.common.file_type import FileType
from app.schemas.document_request import DocumentRequest
from app.schemas.success_code import SuccessCode
from app.schemas.success_response import SuccessResponse
from app.services.common.processor import preprocess_data
from app.services.standard.vector_delete import delete_by_standard_id
from app.services.standard.vector_store import vectorize_and_save

standards = Blueprint('standards', __name__, url_prefix="/flask/standards")

@standards.route('/analysis', methods=['POST'])
def process_pdf_from_s3():

  try:
    document_request = DocumentRequest(**request.get_json())
  except ValidationError as e:
    raise e

  status_code = HTTPStatus.OK
  try:
    if document_request.type == FileType.PDF:
      chunks = preprocess_data(document_request)

      # 5️⃣ 벡터화 + Qdrant 저장
      vectorize_and_save(chunks, "standard", document_request)
  except Exception as e:
    raise e

  return SuccessResponse(SuccessCode.ANALYSIS_COMPLETE, "success").of(), status_code


@standards.route('/<standardId>', methods=["DELETE"])
def delete_standard(standardId: str):
  success_code = delete_by_standard_id(int(standardId))
  return SuccessResponse(success_code, "success").of(), HTTPStatus.OK