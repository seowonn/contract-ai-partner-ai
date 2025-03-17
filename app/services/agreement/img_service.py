import base64

from botocore.response import StreamingBody

from app.blueprints.agreement.agreement_exception import AgreementException
from app.common.exception.error_code import ErrorCode
from app.services.common.s3_service import read_s3_stream
from app.containers.service_container import vision_service


def read_by_byte(s3_stream: StreamingBody) -> bytes:
  return read_s3_stream(s3_stream)


def bytes_to_base64_str(image_bytes: bytes) -> str:
  try:
    return base64.b64encode(image_bytes).decode('utf-8')
  except (TypeError, UnicodeDecodeError):
    raise AgreementException(ErrorCode.FILE_ENCODING_FAILED)


def call_vision_api(base64_image: str) -> str:
  return vision_service.extract_text_by_vision(base64_image)
