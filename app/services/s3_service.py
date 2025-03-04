import io
import boto3
from config.s3_config import (AWS_S3_BUCKET_REGION, AWS_ACCESS_KEY,
                              AWS_SECRET_ACCESS_KEY)


def s3_connection():
  try:
    s3_client = boto3.client(
        service_name="s3",
        region_name=AWS_S3_BUCKET_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
  except Exception as e:
    print(e)
    # exit(ERROR_S3_CONNECTION_FAILED)
  else:
    print("s3 bucket connected!")
    return s3_client


s3 = s3_connection()


def s3_get_object(s3_path):
  if not s3_path.startswith("s3://"):
    raise ValueError("Invalid S3 path")

  parts = s3_path.replace("s3://", "").split("/", 1)
  bucket_name, object_key = parts[0], parts[1]

  # S3에서 파일 가져오기(스트림)
  response = s3.get_object(Bucket=bucket_name, Key=object_key)
  file_stream = response['Body'].read()  # 바이너리 데이터로 읽기

  return io.BytesIO(file_stream)  # BytesIO 객체로 변환하여 반환
