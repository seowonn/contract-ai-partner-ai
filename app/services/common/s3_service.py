import boto3
from botocore.exceptions import ClientError
from botocore.response import StreamingBody

from app.blueprints.agreement.agreement_exception import AgreementException
from app.common.exception.custom_exception import BaseCustomException
from app.common.exception.error_code import ErrorCode
from config.s3_config import AWS_S3_BUCKET_REGION

import os
from dotenv import load_dotenv

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
    raise BaseCustomException(ErrorCode.S3_CLIENT_ERROR)

s3 = s3_connection()


def s3_get_object(s3_path):
  if not s3_path.startswith("s3://"):
    raise ValueError("Invalid S3 path")

  parts = s3_path.replace("s3://", "").split("/", 1)
  bucket_name, object_key = parts[0], parts[1]

  # S3에서 파일 가져오기(스트림)
  # get_object는 내부적으로 ClientError를 발생시킴
  try:
    response = s3.get_object(Bucket=bucket_name, Key=object_key)
    if not response:
      raise BaseCustomException(ErrorCode.FILE_LOAD_FAILED)
    return response['Body']
  except ClientError:
    raise BaseCustomException(ErrorCode.S3_CLIENT_ERROR)


def read_s3_stream(s3_stream: StreamingBody):
  try:
    return s3_stream.read()
  except (OSError, IOError):
    raise BaseCustomException(ErrorCode.S3_STREAM_READ_FAILED)


def generate_pre_signed_url(s3_path: str, expiration=3600) -> str:
  if not s3_path.startswith("s3://"):
    raise AgreementException(ErrorCode.INVALID_S3_PATH)

  parts = s3_path.replace("s3://", "").split("/", 1)
  bucket_name, object_key = parts[0], parts[1]

  try:
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_name, "Key": object_key},
        ExpiresIn=expiration
    )
    return url
  except ClientError:
    raise AgreementException(ErrorCode.S3_CLIENT_ERROR)