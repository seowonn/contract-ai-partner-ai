import boto3
from botocore.exceptions import ClientError
from botocore.response import StreamingBody

from app.blueprints.agreement.agreement_exception import AgreementException
from app.common.exception.custom_exception import CommonException
from app.common.exception.error_code import ErrorCode
from config.s3_config import AWS_S3_BUCKET_REGION
import requests
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
    raise CommonException(ErrorCode.S3_CLIENT_ERROR)

s3 = s3_connection()


def s3_get_object(url: str) -> bytes:
  if not url.startswith("https://"):
    raise ValueError("Invalid https path")

  parts = url.replace("https://", "").split("/", 1)
  bucket_name, object_key = parts[0], parts[1]

  try:
    full_url = f"https://{bucket_name}/{object_key}"

    # 공개된 객체는 generate_pre_signed_url 없이 https:// URL을 그대로 사용하여 접근
    response = requests.get(full_url)

    if response.status_code != 200:
      print(
          f"Failed to fetch the file, Status code: {response.status_code}, Response: {response.text}")  # 디버깅용 출력
      raise CommonException(ErrorCode.FILE_LOAD_FAILED)

    return response.content   # 파일 데이터 반환

  except requests.exceptions.RequestException as e:
    print(f"Error occurred while fetching the file: {e}")
    raise CommonException(ErrorCode.S3_CLIENT_ERROR)


def read_s3_stream(s3_stream: StreamingBody):
  try:
    return s3_stream.read()
  except (OSError, IOError):
    raise CommonException(ErrorCode.S3_STREAM_READ_FAILED)


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