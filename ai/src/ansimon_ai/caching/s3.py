import os
from dotenv import load_dotenv

import boto3
from botocore.exceptions import ClientError


load_dotenv()
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

_s3_client = None

def get_s3_client():
    global _s3_client

    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            region_name=AWS_REGION,
            endpoint_url=f"https://s3.{AWS_REGION}.amazonaws.com",
        )

    return _s3_client

def upload_s3_object(bucket: str, key: str, body: bytes) -> None:
    """S3 객체 업로드."""
    client = get_s3_client()
    client.put_object(Bucket=bucket, Key=key, Body=body)

def head_s3_object(bucket: str, key: str) -> dict | None:
    """S3 객체 존재 여부 확인. 없으면 None."""
    try:
        client = get_s3_client()
        return client.head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "404":
            return None
        if code == "403":
            return None
        raise

def download_s3_object(bucket: str, key: str) -> bytes:
    """S3 객체 다운로드."""
    client = get_s3_client()
    response = client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


