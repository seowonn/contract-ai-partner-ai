import pdfplumber
import io

from app.common.exception.custom_exception import BaseCustomException
from app.common.exception.error_code import ErrorCode


def extract_text_from_pdf_io(pdf_bytes_io):
    if not isinstance(pdf_bytes_io, io.BytesIO):
        raise BaseCustomException(ErrorCode.DATA_TYPE_NOT_MATCH)

    extracted_text = []

    with pdfplumber.open(pdf_bytes_io) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                extracted_text.append(text.strip())

    return "\n".join(extracted_text) # 리스트 사용 문자열 결합 최적화


def extract_text_from_pdf_path(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
    return text



