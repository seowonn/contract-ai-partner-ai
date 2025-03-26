import io
from typing import List

import fitz

from pdfminer.pdfparser import PDFSyntaxError

from app.common.exception.custom_exception import BaseCustomException
from app.common.exception.error_code import ErrorCode
from app.schemas.document import Document, DocumentMetadata


def convert_to_bytes_io(s3_stream: bytes) -> io.BytesIO:
  try:
    pdf_bytes_io = io.BytesIO(s3_stream)
    pdf_bytes_io.seek(0)
    return pdf_bytes_io
  except Exception:
    raise BaseCustomException(ErrorCode.CONVERT_TO_IO_FAILED)


def extract_documents_from_pdf_io2(pdf_bytes_io: io.BytesIO) -> List[Document]:
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
    raise BaseCustomException(ErrorCode.FILE_FORMAT_INVALID)

  return documents

def extract_documents_from_pdf_io(pdf_bytes_io):
  if not isinstance(pdf_bytes_io, io.BytesIO):
    raise BaseCustomException(ErrorCode.DATA_TYPE_NOT_MATCH)

  extracted_text = []

  try:
    # PyMuPDF (fitz) 사용
    # stream 인자가 없으면 BytesIO 인식 못하므로 필수 (파일이 아닌 메모리로부터 찾기)
    doc = fitz.open(stream=pdf_bytes_io, filetype="pdf")
    page_count = doc.page_count
    for page_num in range(page_count):
      try:
        page = doc.load_page(page_num)
        text = page.get_text()
        if text:
          extracted_text.append((page_num + 1, text.strip()))  # 페이지 번호와 텍스트 튜플로 저장
      except (AttributeError, TypeError):
        raise BaseCustomException(ErrorCode.INNER_DATA_ERROR)

  except (PDFSyntaxError, ValueError):
    raise BaseCustomException(ErrorCode.FILE_FORMAT_INVALID)

  return extracted_text

