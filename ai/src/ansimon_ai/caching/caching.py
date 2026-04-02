import json

from botocore.exceptions import ClientError
from sqlalchemy import select

from ansimon_ai.caching.db import SessionLocal
from ansimon_ai.caching.models import Caching
from ansimon_ai.caching.s3 import (
    S3_BUCKET_NAME,
    download_s3_object,
    upload_s3_object,
)


def cache_json(hash_key: str, json_data: dict) -> None:
    """
    hash_key와 JSON 데이터를 받아 S3에 업로드 후 DB에 저장.

    - S3 경로: caching/{hash_key}
    - DB에 hash_key, s3_key 저장
    """
    s3_key = f"caching/{hash_key}"
    json_body = json.dumps(json_data, ensure_ascii=False).encode("utf-8")

    upload_s3_object(S3_BUCKET_NAME, s3_key, json_body)

    with SessionLocal() as session:
        existing = session.scalar(select(Caching).where(Caching.hash_key == hash_key))
        if existing is None:
            session.add(Caching(hash_key=hash_key, s3_key=s3_key))
            session.commit()


def load_cached_json(hash_key: str) -> dict | None:
    """hash_key로 캐싱된 JSON을 불러옴. 없으면 None 반환."""
    with SessionLocal() as session:
        record = session.scalar(select(Caching).where(Caching.hash_key == hash_key))
        if record is None:
            return None

    s3_key = f"caching/{hash_key}"
    try:
        body = download_s3_object(S3_BUCKET_NAME, s3_key)
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "403"):
            return None
        raise

    return json.loads(body.decode("utf-8"))
