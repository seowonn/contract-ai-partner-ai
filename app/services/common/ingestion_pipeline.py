from typing import List

from app.common.exception.custom_exception import BaseCustomException
from app.common.exception.error_code import ErrorCode
from app.schemas.chunk_schema import ArticleChunk
from app.schemas.document_request import DocumentRequest
from app.services.common.chunking_service import chunk_by_article_and_clause_with_page
from app.services.common.pdf_service import convert_to_bytes_io, \
  extract_text_and_documents_from_pdf_io
from app.services.common.s3_service import s3_get_object

import logging
import time


def preprocess_data(document_request: DocumentRequest) -> list:
    # 1️⃣ s3에서 문서(pdf) 가져오기 (메모리 내)
    start_time = time.time()  # 시작 시간 기록
    s3_stream = s3_get_object(document_request.url)
    s3_time = time.time() - start_time  # 경과 시간 계산
    logging.info(f"s3_get_object took {s3_time:.4f} seconds")

    # 2️⃣ PDF 스트림으로 변환
    start_time = time.time()  # 시작 시간 기록
    pdf_bytes_io = convert_to_bytes_io(s3_stream)
    convert_time = time.time() - start_time  # 경과 시간 계산
    logging.info(f"convert_to_bytes_io took {convert_time:.4f} seconds")

    # 3️⃣ PDF에서 텍스트 추출
    start_time = time.time()  # 시작 시간 기록
    extracted_text = extract_text_and_documents_from_pdf_io(pdf_bytes_io)
    extract_time = time.time() - start_time  # 경과 시간 계산
    logging.info(f"extract_text_from_pdf_io took {extract_time:.4f} seconds")

    return extracted_text



def chunk_texts(extracted_text: list) -> List[ArticleChunk]:
  start_time = time.time()  # 시작 시간 기록
  # 4️⃣ 텍스트 청킹
  chunks = chunk_by_article_and_clause_with_page(extracted_text)
  chunk_time = time.time() - start_time  # 경과 시간 계산
  logging.info(
    f"chunk_by_article_and_clause_with_page took {chunk_time:.4f} seconds")

  if len(chunks) == 0:
    raise BaseCustomException(ErrorCode.CHUNKING_FAIL)
  return chunks