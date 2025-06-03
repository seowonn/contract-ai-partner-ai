import io
from typing import List, Tuple

import fitz
import requests

from app.common.exception.custom_exception import CommonException
from app.common.exception.error_code import ErrorCode
from app.schemas.chunk_schema import Document, DocumentMetadata
from app.schemas.document_request import DocumentRequest


def extract_fitz_document_from_pdf_io(
    pdf_bytes_io: io.BytesIO) -> fitz.Document:
  try:
    return fitz.open(stream=pdf_bytes_io, filetype="pdf")
  except Exception:
    raise CommonException(ErrorCode.FILE_FORMAT_INVALID)


def parse_pdf_to_documents(doc: fitz.Document) -> List[Document]:
  documents: List[Document] = []

  for page in doc:
    text = page.get_text("text").strip()

    if text:
      meta = DocumentMetadata(page=page.number + 1)
      documents.append(Document(
          page_content=text,
          metadata=meta
      ))

  if not documents:
    raise CommonException(ErrorCode.NO_TEXTS_EXTRACTED)

  return documents


def load_pdf(document_request: DocumentRequest) -> Tuple[
  List[Document], fitz.Document]:
  try:
    pdf_bytes_io = download_file_as_io(document_request.url)
    fitz_document = extract_fitz_document_from_pdf_io(pdf_bytes_io)
    documents = parse_pdf_to_documents(fitz_document)
  except Exception:
    raise CommonException(ErrorCode.PDF_LOAD_FAILED)

  return documents, fitz_document


def download_file_as_io(url: str):
  try:
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
      raise CommonException(ErrorCode.FILE_LOAD_FAILED)
    return io.BytesIO(response.content)

  except Exception:
    raise CommonException(ErrorCode.INVALID_FILE_STREAM)
