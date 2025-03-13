import pdfplumber
import io

from pdfminer.pdfparser import PDFSyntaxError

from app.common.exception.custom_exception import BaseCustomException
from app.common.exception.error_code import ErrorCode


def convert_to_bytes_io(s3_stream):
  try:
    pdf_bytes_io = io.BytesIO(s3_stream.read())
    pdf_bytes_io.seek(0)
    return pdf_bytes_io
  except Exception:
    raise BaseCustomException(ErrorCode.CONVERT_TO_IO_FAILED)


def extract_text_from_pdf_io(pdf_bytes_io):
  if not isinstance(pdf_bytes_io, io.BytesIO):
    raise BaseCustomException(ErrorCode.DATA_TYPE_NOT_MATCH)

  extracted_text = []

  try:
    with pdfplumber.open(pdf_bytes_io) as pdf:
      for page in pdf.pages:
        try:
          text = page.extract_text()
          if text:
            extracted_text.append(text.strip())
        except (AttributeError, TypeError):
          raise BaseCustomException(ErrorCode.INNER_DATA_ERROR)
  except (PDFSyntaxError, ValueError):
    raise BaseCustomException(ErrorCode.FILE_FORMAT_INVALID)

  return "\n".join(extracted_text)  # 리스트 사용 문자열 결합 최적화


def extract_text_from_pdf_path(pdf_path):
  try:
    with pdfplumber.open(pdf_path) as pdf:
      for page in pdf.pages:
        text = page.extract_text()
  except (PDFSyntaxError, ValueError):
    raise BaseCustomException(ErrorCode.FILE_FORMAT_INVALID)

  return text



