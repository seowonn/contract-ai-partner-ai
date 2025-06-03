import os

import boto3
from botocore.response import StreamingBody
from dotenv import load_dotenv

from app.common.exception.custom_exception import CommonException
from app.common.exception.error_code import ErrorCode
from config.s3_config import AWS_S3_BUCKET_REGION

load_dotenv()

def s3_connection():
  try:
    return boto3.client(
        service_name="s3",
        region_name=AWS_S3_BUCKET_REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )
  except Exception:
    raise CommonException(ErrorCode.S3_CLIENT_ERROR)

s3 = s3_connection()


def read_s3_stream(s3_stream: StreamingBody):
  try:
    return s3_stream.read()
  except (OSError, IOError):
    raise CommonException(ErrorCode.S3_STREAM_READ_FAILED)
