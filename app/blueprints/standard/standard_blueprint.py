from flask import Blueprint, request, jsonify

from app.blueprints.standard.standard_exception import StandardException
from app.common.exception.custom_exception import BaseCustomException
from app.common.exception.error_code import ErrorCode
from app.schemas.pdf_request import PDFRequest
from app.services.standard import processor

standard = Blueprint('reference_document', __name__, url_prefix="/flask/reference-document")

@standard.route('', methods=['POST'])
def process_pdf_from_s3():

  try:
    pdf_request = PDFRequest(**request.get_json())
  except Exception:
    raise StandardException(ErrorCode.REQUEST_NOT_MATCH)

  try:
    response, status_code = processor.process_pdf(pdf_request)
  except (StandardException, BaseCustomException) as e:
    raise e
  except Exception:
    raise StandardException(ErrorCode.UPLOAD_FAIL)

  return jsonify(response), status_code
