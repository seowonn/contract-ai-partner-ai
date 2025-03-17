from botocore.response import StreamingBody

from app.services.common.s3_service import read_s3_stream


def read_by_byte(s3_stream: StreamingBody):
  return read_s3_stream(s3_stream)