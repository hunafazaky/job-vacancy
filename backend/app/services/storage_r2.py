import uuid

import boto3
from botocore.config import Config

from app.core.config import settings


def _client():
    endpoint_url = f"https://{settings.r2_account_id}.r2.cloudflarestorage.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def upload_image(data: bytes, content_type: str, user_id: str) -> str:
    """
    Uploads optimized image bytes to R2 and returns the public URL.
    Called only for signed-in users (see extract.py) — anonymous uploads
    never reach this function, so no anonymous image ever touches R2.
    """
    key = f"extractions/{user_id}/{uuid.uuid4()}.jpg"
    client = _client()
    client.put_object(
        Bucket=settings.r2_bucket_name,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return f"{settings.r2_public_base_url.rstrip('/')}/{key}"
