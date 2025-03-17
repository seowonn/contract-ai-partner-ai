from app.schemas.document_request import DocumentRequest
from app.services.common.chunking_service import chunk_by_article_and_clause
from app.services.common.img_service import read_by_byte
from app.services.common.pdf_service import extract_text_from_pdf_io, \
  convert_to_bytes_io
from app.services.common.s3_service import s3_get_object
from app.services.standard.vector_store import vectorize_and_save

import base64

def process_pdf(pdf_request: DocumentRequest):
  # 1️⃣ s3에서 문서(pdf) 가져오기 (메모리 내)
  s3_stream = s3_get_object(pdf_request.url)

  # 2️⃣ PDF 스트림으로 변환
  pdf_bytes_io = convert_to_bytes_io(s3_stream)

  # 3️⃣ PDF에서 텍스트 추출
  extracted_text = extract_text_from_pdf_io(pdf_bytes_io)

  # 4️⃣ 텍스트 청킹
  chunks = chunk_by_article_and_clause(extracted_text)

  # 5️⃣ 벡터화 + Qdrant 저장
  vectorize_and_save(chunks, "standard", pdf_request)

  return 200


def process_img(img_reqeust: DocumentRequest):
  s3_stream = s3_get_object(img_reqeust.url)

  image_bytes = read_by_byte(s3_stream)
  image_bytes = s3_stream.read()

  # Vision API에 넣기 위해 문자열로 변환(decode)함
  base64_image = base64.b64encode(image_bytes).decode('utf-8')

  # Vision API 호출


  return None