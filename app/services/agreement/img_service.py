from botocore.response import StreamingBody

from app.containers.service_container import vision_service
from app.schemas.document_request import DocumentRequest
from app.services.common.s3_service import read_s3_stream, \
  generate_pre_signed_url


def process_img(img_reqeust: DocumentRequest) -> str:
  pre_signed_url = generate_pre_signed_url(img_reqeust.url)
  extracted_text = call_vision_api(pre_signed_url)
  return extracted_text


def read_by_byte(s3_stream: StreamingBody) -> bytes:
  return read_s3_stream(s3_stream)


def call_vision_api(base64_image: str) -> str:
  return vision_service.extract_text_by_vision(base64_image)
