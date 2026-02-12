"""
S3-compatible object storage service for report artifacts.

Uploads generated HTML/PDF reports to MinIO (dev) or AWS S3 (prod).
"""

import logging
from typing import Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger("sentinelforge.s3")


def _get_client():
    """Get S3 client configured from settings."""
    from config import settings

    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT or None,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
    )


def upload_report(
    content: bytes,
    key: str,
    content_type: str = "text/html",
    bucket: Optional[str] = None,
) -> str:
    """Upload report content to S3 and return the key.

    Args:
        content: Raw bytes to upload.
        key: S3 object key (e.g. "reports/<run_id>.html").
        content_type: MIME type for the object.
        bucket: Override bucket name. Defaults to settings.S3_BUCKET.

    Returns:
        The S3 key of the uploaded object.

    Raises:
        ClientError: On S3 upload failure.
    """
    from config import settings

    bucket = bucket or settings.S3_BUCKET
    client = _get_client()

    try:
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )
        logger.info(f"Uploaded report to s3://{bucket}/{key} ({len(content)} bytes)")
        return key
    except ClientError as e:
        logger.error(f"S3 upload failed for {key}: {e}")
        raise


def download_report(key: str, bucket: Optional[str] = None) -> Optional[bytes]:
    """Download report content from S3.

    Returns:
        Raw bytes of the object, or None on failure.
    """
    from config import settings

    bucket = bucket or settings.S3_BUCKET
    client = _get_client()

    try:
        response = client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()
    except ClientError as e:
        logger.error(f"S3 download failed for {key}: {e}")
        return None


def generate_presigned_url(
    key: str,
    bucket: Optional[str] = None,
    expires_in: int = 3600,
) -> Optional[str]:
    """Generate a presigned URL for temporary download access.

    Args:
        key: S3 object key.
        bucket: Override bucket name.
        expires_in: URL validity in seconds (default 1 hour).

    Returns:
        Presigned URL string, or None on failure.
    """
    from config import settings

    bucket = bucket or settings.S3_BUCKET
    client = _get_client()

    try:
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )
        return url
    except ClientError as e:
        logger.error(f"Presigned URL generation failed for {key}: {e}")
        return None
