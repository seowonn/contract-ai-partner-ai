from app.schemas.pdf_request import PDFRequest
from app.services.common.chunking_service import chunk_by_article_and_clause
from app.services.common.pdf_service import extract_text_from_pdf_io, \
  convert_to_bytes_io
from app.services.common.s3_service import s3_get_object
from app.services.standard.vector_store import vectorize_and_save


def process_pdf(pdf_request: PDFRequest):
  # 1️⃣ s3에서 문서(pdf) 가져오기 (메모리 내)
  s3_stream = s3_get_object(pdf_request.s3Path)

  # 2️⃣ PDF 스트림으로 변환
  pdf_bytes_io = convert_to_bytes_io(s3_stream)

  # 3️⃣ PDF에서 텍스트 추출
  extracted_text = extract_text_from_pdf_io(pdf_bytes_io)

  # 4️⃣ 텍스트 청킹
  chunks = chunk_by_article_and_clause(extracted_text)

  # 5️⃣ 벡터화 + Qdrant 저장
  vectorize_and_save(chunks, "standard", pdf_request)

  return 200

