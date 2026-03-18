import boto3
from botocore.exceptions import ClientError

from app.core.settings import settings


def get_cognito_client():
    print(f"AWS_REGION: {settings.AWS_REGION}")
    return boto3.client(
        "cognito-idp",
        region_name=settings.AWS_REGION,
    )


def get_s3_client():
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        endpoint_url=f"https://s3.{settings.AWS_REGION}.amazonaws.com",
    )


def download_s3_object(bucket: str, key: str) -> bytes:
    """S3 객체 다운로드."""
    client = get_s3_client()
    response = client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


def download_s3_object_with_metadata(bucket: str, key: str) -> tuple[bytes, dict]:
    """S3 객체 다운로드 + 메타데이터(ContentType 등) 반환."""
    client = get_s3_client()
    response = client.get_object(Bucket=bucket, Key=key)
    body = response["Body"].read()
    meta = {
        "ContentType": response.get("ContentType"),
        **response.get("Metadata", {}),
    }
    return body, meta


def head_s3_object(bucket: str, key: str) -> dict | None:
    """S3 객체 존재 여부 및 메타데이터 확인. 없으면 None."""
    try:
        client = get_s3_client()
        return client.head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "404":
            return None
        if code == "403":
            return None  # 객체 없을 때 일부 설정에서 403 반환
        raise
