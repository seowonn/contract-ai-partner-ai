import time
from typing import List

from app.schemas.chunk_schema import ArticleChunk
from app.schemas.document_request import DocumentRequest
from app.services.common.chunking_service import chunk_by_article_and_clause
from app.services.common.pdf_service import convert_to_bytes_io, extract_text_from_pdf_io
from app.services.common.s3_service import s3_get_object


def preprocess_data(document_request: DocumentRequest) -> str:
    # 1️⃣ s3에서 문서(pdf) 가져오기 (메모리 내)
    start_time = time.time()  # 시작 시간 기록
    s3_stream = s3_get_object(document_request.url)
    end_time = time.time()  # 끝 시간 기록
    print(f"Time taken to fetch from S3: {end_time - start_time:.4f} seconds")

    # 2️⃣ PDF 스트림으로 변환
    start_time = time.time()
    pdf_bytes_io = convert_to_bytes_io(s3_stream)
    end_time = time.time()
    print(f"Time taken to convert PDF to bytes: {end_time - start_time:.4f} seconds")

    # 3️⃣ PDF에서 텍스트 추출
    start_time = time.time()
    extracted_text = extract_text_from_pdf_io(pdf_bytes_io)
    end_time = time.time()
    print(f"Time taken to extract text from PDF: {end_time - start_time:.4f} seconds")

    return extracted_text


def chunk_texts(extracted_text: str) -> List[ArticleChunk]:
    # 4️⃣ 텍스트 청킹
    start_time = time.time()
    chunks = chunk_by_article_and_clause(extracted_text)
    end_time = time.time()
    print(f"Time taken to chunk texts: {end_time - start_time:.4f} seconds")

    return chunks
