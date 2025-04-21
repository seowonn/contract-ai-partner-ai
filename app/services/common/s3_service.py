import os

import boto3
import requests
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


def s3_get_object(url: str) -> bytes:
  try:
    response = requests.get(url, timeout=10)

    if response.status_code != 200:
      raise CommonException(ErrorCode.FILE_LOAD_FAILED)

    return response.content

  except Exception:
    raise CommonException(ErrorCode.S3_CLIENT_ERROR)


def read_s3_stream(s3_stream: StreamingBody):
  try:
    return s3_stream.read()
  except (OSError, IOError):
    raise CommonException(ErrorCode.S3_STREAM_READ_FAILED)
