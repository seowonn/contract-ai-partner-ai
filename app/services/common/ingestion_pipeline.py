import io
from typing import List, Tuple

from app.common.constants import CLAUSE_TEXT_SEPARATOR
from app.common.exception.custom_exception import BaseCustomException
from app.common.exception.error_code import ErrorCode
from app.schemas.analysis_response import RagResult, ClauseData
from app.schemas.chunk_schema import ArticleChunk, DocumentChunk
from app.schemas.chunk_schema import Document
from app.schemas.document_request import DocumentRequest
from app.services.common.chunking_service import \
  chunk_by_article_and_clause_with_page, chunk_by_article_and_clause
from app.services.common.pdf_service import convert_to_bytes_io, \
  extract_documents_from_pdf_io
from app.services.common.s3_service import s3_get_object

import logging
import time


def preprocess_data(document_request: DocumentRequest) -> List[Document]:
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
  documents = extract_documents_from_pdf_io(pdf_bytes_io)
  extract_time = time.time() - start_time  # 경과 시간 계산
  logging.info(
    f"extract_text_and_documents_from_pdf_io took {extract_time:.4f} seconds")

  return documents


def preprocess_data2(document_request: DocumentRequest) -> Tuple[
  List[Document], io.BytesIO]:
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
  documents = extract_documents_from_pdf_io(pdf_bytes_io)
  extract_time = time.time() - start_time  # 경과 시간 계산
  logging.info(
      f"extract_text_and_documents_from_pdf_io took {extract_time:.4f} seconds")

  return documents, pdf_bytes_io


def chunk_standard_texts(extracted_text: str) -> List[ArticleChunk]:
  start_time = time.time()
  chunks = chunk_by_article_and_clause(extracted_text)
  logging.info(f"chunk_standard_texts 소요 시간: {time.time() - start_time}")

  if len(chunks) == 0:
    raise BaseCustomException(ErrorCode.CHUNKING_FAIL)
  return chunks


def chunk_agreement_documents(documents: List[Document]) -> List[DocumentChunk]:
  start_time = time.time()  # 시작 시간 기록
  # 4️⃣ 텍스트 청킹
  chunks = chunk_by_article_and_clause_with_page(documents)
  chunk_time = time.time() - start_time  # 경과 시간 계산
  logging.info(f"chunk_agreement_texts took {chunk_time:.4f} seconds")

  if len(chunks) == 0:
    raise BaseCustomException(ErrorCode.CHUNKING_FAIL)
  return chunks


def combine_chunks_by_clause_number(document_chunks: List[DocumentChunk]) -> \
List[RagResult]:
  combined_chunks: List[RagResult] = []
  clause_map: dict[str, RagResult] = {}

  for doc in document_chunks:
    rag_result = clause_map.setdefault(doc.clause_number, RagResult())

    if rag_result.incorrect_text:
      rag_result.incorrect_text = (
        CLAUSE_TEXT_SEPARATOR.join(clause_map[doc.clause_number].incorrect_text))
    else:
      rag_result.incorrect_text = doc.clause_content
      combined_chunks.append(rag_result)

    rag_result.clause_data.append(ClauseData(
        order_index=doc.order_index,
        page=doc.page
    ))

  return combined_chunks