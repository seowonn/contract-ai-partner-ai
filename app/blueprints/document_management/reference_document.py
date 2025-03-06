import io

from flask import Blueprint, request, jsonify

from app.blueprints.document_management.models import PDFRequest
from app.services import s3_service, pdf_service, chunking
from app.services import vector_store

bp = Blueprint('reference_document', __name__, url_prefix="/flask/reference-document")

@bp.route('', methods=['POST'])
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

  try:
    # 1️⃣ s3에서 문서(pdf) 가져오기 (메모리 내)
    s3_stream = s3_service.s3_get_object(pdf_request.s3_path)

    if s3_stream is None:
      raise FileNotFoundError(f"S3에서 파일을 찾을 수 없습니다: {pdf_request.s3_path}")

    pdf_bytes_io = io.BytesIO(s3_stream.read())
    pdf_bytes_io.seek(0)

    # 2️⃣ PDF에서 텍스트 추출
    extracted_text = pdf_service.extract_text_from_pdf_io(pdf_bytes_io)

    # 3️⃣ 텍스트 청킹
    chunks = chunking.chunk_by_article_and_clause(extracted_text)

    # 4️⃣ 벡터화 + Qdrant 저장
    vector_store.embed_chunks(chunks, "reference_document",
                              pdf_request.category, pdf_request.reference_id)

    return jsonify({"uploadResult": True})

  except ValueError as e:
    return jsonify({"error": str(e)}), 400
  except Exception as e:
    return jsonify({"error": "S3 download failed", "details": str(e)}), 500
