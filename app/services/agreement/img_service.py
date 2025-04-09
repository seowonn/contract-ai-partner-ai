from botocore.response import StreamingBody

from app.containers.service_container import vision_service
from app.services.common.s3_service import read_s3_stream


def read_by_byte(s3_stream: StreamingBody) -> bytes:
  return read_s3_stream(s3_stream)


def call_vision_api(base64_image: str) -> str:
  return vision_service.extract_text_by_vision(base64_image)
