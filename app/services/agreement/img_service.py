import base64
from http import HTTPStatus

from botocore.response import StreamingBody

from app.blueprints.agreement.agreement_exception import AgreementException
from app.common.exception.error_code import ErrorCode
from app.schemas.document_request import DocumentRequest
from app.services.common.s3_service import read_s3_stream, s3_get_object
from app.containers.service_container import vision_service


def process_img(img_reqeust: DocumentRequest):
  s3_stream = s3_get_object(img_reqeust.url)

  image_bytes = read_by_byte(s3_stream)

  # Vision API에 넣기 위해 문자열로 변환(decode)함
  base64_image = bytes_to_base64_str(image_bytes)

  # Vision API 호출
  extracted_text = call_vision_api(base64_image)

  return HTTPStatus.OK


def read_by_byte(s3_stream: StreamingBody) -> bytes:
  return read_s3_stream(s3_stream)


def bytes_to_base64_str(image_bytes: bytes) -> str:
  try:
    return base64.b64encode(image_bytes).decode('utf-8')
  except (TypeError, UnicodeDecodeError):
    raise AgreementException(ErrorCode.FILE_ENCODING_FAILED)


def call_vision_api(base64_image: str) -> str:
  return vision_service.extract_text_by_vision(base64_image)
