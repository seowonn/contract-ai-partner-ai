import io
import fitz

from botocore.response import StreamingBody
from pdfminer.pdfparser import PDFSyntaxError

from app.common.exception.custom_exception import BaseCustomException
from app.common.exception.error_code import ErrorCode
from app.services.common.s3_service import read_s3_stream


def convert_to_bytes_io(s3_stream: StreamingBody):
  try:
    data = read_s3_stream(s3_stream)
    pdf_bytes_io = io.BytesIO(data)
    pdf_bytes_io.seek(0)
    return pdf_bytes_io
  except Exception:
    raise BaseCustomException(ErrorCode.CONVERT_TO_IO_FAILED)

def extract_text_from_pdf_io(pdf_bytes_io):
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

