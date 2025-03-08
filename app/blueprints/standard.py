from flask import Blueprint, request, jsonify

from app.schemas.pdf_request import PDFRequest
from app.services.standard import processor

document = Blueprint('reference_document', __name__, url_prefix="/flask/reference-document")

@document.route('', methods=['POST'])
def process_pdf_from_s3():
  data = request.get_json()

  try:
    pdf_request = PDFRequest(
        s3_path=data["s3Path"],
        category=data["category"],
        reference_id=data["id"]
    )
  except (KeyError, ValueError) as e:
    return jsonify({"error": f"Invalid request: {str(e)}"}), 400

  response, status_code = processor.process_pdf(pdf_request)

  return jsonify(response), status_code
