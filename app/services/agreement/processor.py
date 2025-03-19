from app.schemas.pdf_request import AgreementPDFRequest
from app.services.common.chunking_service import chunk_by_article_and_clause
from app.services.common.pdf_service import extract_text_from_pdf_io, \
  convert_to_bytes_io
from app.services.common.s3_service import s3_get_object
from app.services.agreement.vectorize_similarity import vectorize_and_calculate_similiarity

def process_pdf(pdf_request: AgreementPDFRequest):
  # 1️⃣ s3에서 문서(pdf) 가져오기 (메모리 내)
  s3_stream = s3_get_object(pdf_request.url)

  # 2️⃣ PDF 스트림으로 변환
  pdf_bytes_io = convert_to_bytes_io(s3_stream)

  # 3️⃣ PDF에서 텍스트 추출
  extracted_text = extract_text_from_pdf_io(pdf_bytes_io)

  # 4️⃣ 텍스트 청킹
  chunks = chunk_by_article_and_clause(extracted_text)

  # 5️⃣ 벡터화 + 유사도 비교 (리턴값 추가)
  result = vectorize_and_calculate_similiarity(chunks, pdf_request)

  return result, 200
