import asyncio
from typing import List

from app.schemas.analysis_response import DocumentAnalysisResult
from app.schemas.chunk_schema import ClauseChunk
from app.schemas.chunk_schema import Document
from app.schemas.chunk_schema import DocumentMetadata
from app.schemas.document_request import DocumentRequest
from app.services.agreement.agreement_chunking import chunk_agreement_documents
from app.services.agreement.ocr_service import extract_ocr, \
  vectorize_and_calculate_similarity_ocr
from app.services.agreement.vectorize_similarity import \
  vectorize_and_calculate_similarity
from app.services.common.chunking_service import \
  semantic_chunk, chunk_legal_terms
from app.services.common.pdf_service import load_pdf


def analyze_img_agreement(
    document_request: DocumentRequest) -> DocumentAnalysisResult:
  full_text, all_texts_with_bounding_boxes = extract_ocr(document_request.url)

  documents: List[Document] = [
    Document(page_content=full_text, metadata=DocumentMetadata(page=1))]

  combined_chunks = chunk_agreement_documents(documents)

  # 입력값이 다르기에 함수가 분리되어야 함
  chunks = asyncio.run(
      vectorize_and_calculate_similarity_ocr(combined_chunks, document_request,
                                             all_texts_with_bounding_boxes))

  return DocumentAnalysisResult(chunks=chunks,
                                total_chunks=len(combined_chunks),
                                total_pages=len(documents))


def analyze_pdf_agreement(
    document_request: DocumentRequest) -> DocumentAnalysisResult:

  # PyMuPDF fitz로 document 객체 추출
  documents, fitz_document = load_pdf(document_request)

  # chunking
  combined_chunks = chunk_agreement_documents(documents)

  # embedding + search(rag)
  chunks = asyncio.run(
      vectorize_and_calculate_similarity(combined_chunks, document_request,
                                         fitz_document))

  return DocumentAnalysisResult(chunks=chunks,
                                total_chunks=len(combined_chunks),
                                total_pages=len(documents))


def chunk_standard_texts(documents: List[Document], category: str,
    page_batch_size: int = 50) -> List[ClauseChunk]:
  all_clauses = []

  for start in range(0, len(documents), page_batch_size):
    batch_docs = documents[start:start + page_batch_size]
    extracted_text = "\n".join(doc.page_content for doc in batch_docs)

    if category == "법률용어":
      all_clauses.extend(chunk_legal_terms(extracted_text))
    else:
      article_chunks = semantic_chunk(extracted_text, similarity_threshold=0.3)
      all_clauses.extend(article_chunks)

  return all_clauses
