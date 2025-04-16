import asyncio
import re
from typing import List, Tuple

import fitz

from app.common.constants import CLAUSE_TEXT_SEPARATOR
from app.common.exception.custom_exception import CommonException
from app.common.exception.error_code import ErrorCode
from app.common.file_type import FileType
from app.schemas.analysis_response import RagResult, ClauseData
from app.schemas.chunk_schema import Document
from app.schemas.chunk_schema import DocumentChunk, DocumentMetadata
from app.schemas.document_request import DocumentRequest
from app.services.agreement.ocr_service import \
  chunk_by_article_and_clause_without_page_ocr
from app.services.agreement.vectorize_similarity import \
  vectorize_and_calculate_similarity_ocr, vectorize_and_calculate_similarity
from app.services.agreement.vision_service import extract_ocr
from app.services.common.chunking_service import \
  chunk_by_article_and_clause_with_page, semantic_chunk
from app.services.common.pdf_service import convert_to_bytes_io, \
  parse_pdf_to_documents, extract_fitz_document_from_pdf_io
from app.services.common.s3_service import s3_get_object, \
  generate_pre_signed_url


def ocr_service(document_request: DocumentRequest):
  documents, all_texts_with_bounding_boxes = preprocess_data_ocr(
      document_request)
  document_chunks = chunk_agreement_documents_ocr(documents)
  combined_chunks = combine_chunks_by_clause_number_ocr(document_chunks)
  chunks = asyncio.run(
      vectorize_and_calculate_similarity_ocr(combined_chunks, document_request,
                                             all_texts_with_bounding_boxes))
  return chunks, len(combined_chunks), len(documents)


def pdf_agreement_service(document_request: DocumentRequest) -> Tuple[
  List[RagResult], int, int]:
  s3_stream = s3_get_object(document_request.url)
  pdf_bytes_io = convert_to_bytes_io(s3_stream)
  fitz_document = extract_fitz_document_from_pdf_io(pdf_bytes_io)
  documents = parse_pdf_to_documents(fitz_document)
  document_chunks = chunk_agreement_documents(documents)
  combined_chunks = combine_chunks_by_clause_number(document_chunks)
  chunks = asyncio.run(
      vectorize_and_calculate_similarity(combined_chunks, document_request,
                                         fitz_document))
  return chunks, len(combined_chunks), len(documents)


def preprocess_data(document_request: DocumentRequest) -> Tuple[
  List[Document], fitz.Document]:
  documents: List[Document] = []
  fitz_document = None

  file_type = extract_file_type(document_request.url)
  if file_type in (FileType.PNG, FileType.JPG, FileType.JPEG):
    pre_signed_url = generate_pre_signed_url(document_request.url)
  elif file_type == FileType.PDF:
    s3_stream = s3_get_object(document_request.url)
    pdf_bytes_io = convert_to_bytes_io(s3_stream)
    fitz_document = extract_fitz_document_from_pdf_io(pdf_bytes_io)
    documents = parse_pdf_to_documents(fitz_document)
  else:
    raise CommonException(ErrorCode.UNSUPPORTED_FILE_TYPE)

  if not documents:
    raise CommonException(ErrorCode.NO_TEXTS_EXTRACTED)
  return documents, fitz_document


def preprocess_data_ocr(document_request: DocumentRequest) -> Tuple[
  List[Document], List[dict]]:
  documents: List[Document] = []
  all_texts_with_bounding_boxes = None

  file_type = extract_file_type(document_request.url)
  if file_type in (FileType.PNG, FileType.JPG, FileType.JPEG):
    full_text, all_texts_with_bounding_boxes = extract_ocr(document_request.url)

    documents.append(Document(
        page_content=full_text
    ))

  else:
    raise CommonException(ErrorCode.UNSUPPORTED_FILE_TYPE)

  if len(documents) == 0:
    raise CommonException(ErrorCode.NO_TEXTS_EXTRACTED)
  return documents, all_texts_with_bounding_boxes


def extract_file_type(url: str) -> FileType:
  try:
    ext = url.split(".")[-1].strip().upper()
    return FileType(ext)
  except Exception:
    raise CommonException(ErrorCode.UNSUPPORTED_FILE_TYPE)


def chunk_standard_texts(extracted_text: str) -> List[str]:
  chunks = semantic_chunk(
      extracted_text,
      similarity_threshold=0.6
  )
  if not chunks:
    raise CommonException(ErrorCode.CHUNKING_FAIL)
  return chunks


def chunk_agreement_documents(documents: List[Document]) -> List[DocumentChunk]:
  chunks = chunk_by_article_and_clause_with_page(documents)
  keep_text, _ = chunks[0].clause_content.split("1.", 1)
  chunks[0].clause_content = keep_text
  keep_text, _ = chunks[-2].clause_content.split("날짜 :", 1)
  chunks[-2].clause_content = keep_text.strip()
  del chunks[-1]

  if not chunks:
    raise CommonException(ErrorCode.CHUNKING_FAIL)
  return chunks


def chunk_agreement_documents_ocr(documents: List[Document]) -> List[
  DocumentChunk]:
  chunks = chunk_by_article_and_clause_without_page_ocr(documents)

  if len(chunks) == 0:
    raise CommonException(ErrorCode.CHUNKING_FAIL)
  return chunks


def combine_chunks_by_clause_number(document_chunks: List[DocumentChunk]) -> \
    List[RagResult]:
  combined_chunks: List[RagResult] = []
  clause_map: dict[str, RagResult] = {}

  for doc in document_chunks:
    rag_result = clause_map.setdefault(doc.clause_number, RagResult())

    if rag_result.incorrect_text:
      rag_result.incorrect_text += (
          CLAUSE_TEXT_SEPARATOR + doc.clause_content)
    else:
      rag_result.incorrect_text = doc.clause_content
      combined_chunks.append(rag_result)

    rag_result.clause_data.append(ClauseData(
        order_index=doc.order_index,
        page=doc.page
    ))

  return combined_chunks


def combine_chunks_by_clause_number_ocr(
    document_chunks: List[DocumentChunk]) -> \
    List[RagResult]:
  combined_chunks: List[RagResult] = []

  for doc in document_chunks:
    combined_chunks.append(
        RagResult(
            incorrect_text=doc.clause_content,
            clause_data=[ClauseData(order_index=doc.order_index, page=doc.page)]
        )
    )

  return combined_chunks


def normalize_spacing(text: str) -> str:
  text = text.replace('\n', '[[[NEWLINE]]]')
  text = re.sub(r'\s{5,}', '\n', text)
  text = text.replace('[[[NEWLINE]]]', '\n')
  return text
