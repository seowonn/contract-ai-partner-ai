import io

from app.blueprints.standard.standard_exception import StandardException
from app.common.exception.error_code import ErrorCode
from app.services.common.chunking_service import chunk_by_article_and_clause
from app.services.common.pdf_service import extract_text_from_pdf_io
from app.services.common.s3_service import s3_get_object
from app.services.standard.vector_store import embed_chunks


def process_pdf(pdf_request):
  # 1️⃣ s3에서 문서(pdf) 가져오기 (메모리 내)
  try:
    s3_stream = s3_get_object(pdf_request.s3_path)
  except Exception:
    raise StandardException(ErrorCode.S3FILE_NOT_FOUND)

  pdf_bytes_io = io.BytesIO(s3_stream.read())
  pdf_bytes_io.seek(0)

  # 2️⃣ PDF에서 텍스트 추출
  extracted_text = extract_text_from_pdf_io(pdf_bytes_io)

  # 3️⃣ 텍스트 청킹
  chunks = chunk_by_article_and_clause(extracted_text)

  # 4️⃣ 벡터화 + Qdrant 저장
  embed_chunks(chunks, "standard",
               pdf_request.category, pdf_request.reference_id)

  return {"uploadResult": True}, 200

