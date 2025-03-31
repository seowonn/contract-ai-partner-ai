import io
from typing import List

import fitz

from app.common.exception.custom_exception import CommonException
from app.common.exception.error_code import ErrorCode
from app.schemas.chunk_schema import Document, DocumentMetadata


def convert_to_bytes_io(s3_stream: bytes) -> io.BytesIO:
  try:
    pdf_bytes_io = io.BytesIO(s3_stream)
    pdf_bytes_io.seek(0)
    return pdf_bytes_io
  except Exception:
    raise CommonException(ErrorCode.CONVERT_TO_IO_FAILED)


def extract_documents_from_pdf_io(pdf_bytes_io: io.BytesIO) -> List[Document]:
  documents: List[Document] = []

  try:
    doc = fitz.open(stream=pdf_bytes_io, filetype="pdf")

    for page_num in range(doc.page_count):
      page = doc.load_page(page_num)
      text = page.get_text().strip()

      if text:
        meta = DocumentMetadata(page=page_num + 1)
        documents.append(Document(
            page_content=text,
            metadata=meta
        ))

  except Exception:
    raise CommonException(ErrorCode.FILE_FORMAT_INVALID)

  return documents


def byte_data(pdf_bytes_io: io.BytesIO) -> fitz.Document:
  return fitz.open(stream=pdf_bytes_io, filetype="pdf")