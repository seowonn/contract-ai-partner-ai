import io
from typing import List, Tuple

import fitz

from app.common.exception.custom_exception import CommonException
from app.common.exception.error_code import ErrorCode
from app.schemas.chunk_schema import Document, DocumentMetadata
from app.schemas.document_request import DocumentRequest
from app.services.common.s3_service import s3_get_object


def convert_to_bytes_io(s3_stream: bytes) -> io.BytesIO:
  try:
    return io.BytesIO(s3_stream)
  except Exception:
    raise CommonException(ErrorCode.CONVERT_TO_IO_FAILED)


def extract_fitz_document_from_pdf_io(
    pdf_bytes_io: io.BytesIO) -> fitz.Document:
  try:
    return fitz.open(stream=pdf_bytes_io, filetype="pdf")
  except Exception:
    raise CommonException(ErrorCode.FILE_FORMAT_INVALID)


def parse_pdf_to_documents(doc: fitz.Document) -> List[Document]:
  documents: List[Document] = []

  try:
    for page in doc:
      text = page.get_text("text").strip()

      if text:
        meta = DocumentMetadata(page=page.number + 1)
        documents.append(Document(
            page_content=text,
            metadata=meta
        ))

  except Exception:
    raise CommonException(ErrorCode.PDF_LOAD_FAILED)

  return documents


def preprocess_pdf(document_request: DocumentRequest) -> Tuple[
  List[Document], fitz.Document]:
  s3_stream = s3_get_object(document_request.url)
  pdf_bytes_io = convert_to_bytes_io(s3_stream)
  fitz_document = extract_fitz_document_from_pdf_io(pdf_bytes_io)
  documents = parse_pdf_to_documents(fitz_document)

  if not documents:
    raise CommonException(ErrorCode.NO_TEXTS_EXTRACTED)
  return documents, fitz_document
