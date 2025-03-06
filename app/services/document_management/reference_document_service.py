import io

from app.services import s3_service, chunking, vector_store, pdf_service


def process_pdf(pdf_request):
  try:
    # 1️⃣ s3에서 문서(pdf) 가져오기 (메모리 내)
    s3_stream = s3_service.s3_get_object(pdf_request.s3_path)

    if s3_stream is None:
      raise FileNotFoundError(f"S3에서 파일을 찾을 수 없습니다: {pdf_request.s3_path}")

    pdf_bytes_io = io.BytesIO(s3_stream.read())
    pdf_bytes_io.seek(0)

    # 2️⃣ PDF에서 텍스트 추출
    # extracted_text = pdf_service.extract_text_from_pdf_io(pdf_bytes_io)

    # 3️⃣ 텍스트 청킹
    chunks = chunking.chunk_by_article_and_clause("extracted_text")

    # 4️⃣ 벡터화 + Qdrant 저장
    vector_store.embed_chunks(chunks, "reference_document",
                              pdf_request.category, pdf_request.reference_id)

    return {"uploadResult": True}, 200

  except ValueError as e:
    return {"error": str(e)}, 400
  except Exception as e:
    return {"error": "S3 download failed", "details": str(e)}, 500
