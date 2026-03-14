import io
from minio import Minio
from minio.error import S3Error
from app.config import settings
from app.core.exceptions import StorageError
from functools import lru_cache


@lru_cache
def get_minio_client() -> Minio:
    return Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def ensure_bucket_exists() -> None:
    client = get_minio_client()
    try:
        if not client.bucket_exists(settings.minio_bucket):
            client.make_bucket(settings.minio_bucket)
    except S3Error as e:
        raise StorageError(f"Failed to ensure bucket: {e}")


def upload_file(
    file_data: bytes,
    object_key: str,
    content_type: str,
) -> str:
    """Upload bytes to MinIO and return the object key."""
    client = get_minio_client()
    ensure_bucket_exists()
    try:
        client.put_object(
            bucket_name=settings.minio_bucket,
            object_name=object_key,
            data=io.BytesIO(file_data),
            length=len(file_data),
            content_type=content_type,
        )
        return object_key
    except S3Error as e:
        raise StorageError(f"Upload failed: {e}")


def get_presigned_url(object_key: str, expires_seconds: int = 900) -> str:
    """Get a presigned download URL valid for `expires_seconds` seconds."""
    from datetime import timedelta
    client = get_minio_client()
    try:
        return client.presigned_get_object(
            bucket_name=settings.minio_bucket,
            object_name=object_key,
            expires=timedelta(seconds=expires_seconds),
        )
    except S3Error as e:
        raise StorageError(f"Presign failed: {e}")


def download_file(object_key: str) -> bytes:
    """Download a file from MinIO and return its bytes."""
    client = get_minio_client()
    try:
        response = client.get_object(settings.minio_bucket, object_key)
        data = response.read()
        response.close()
        response.release_conn()
        return data
    except S3Error as e:
        raise StorageError(f"Download failed: {e}")


def delete_file(object_key: str) -> None:
    client = get_minio_client()
    try:
        client.remove_object(settings.minio_bucket, object_key)
    except S3Error as e:
        raise StorageError(f"Delete failed: {e}")


def list_user_files(user_id: str) -> list[dict]:
    """List all files for a user (prefix-based)."""
    client = get_minio_client()
    prefix = f"users/{user_id}/"
    try:
        objects = client.list_objects(settings.minio_bucket, prefix=prefix, recursive=True)
        return [
            {
                "key": obj.object_name,
                "size": obj.size,
                "last_modified": obj.last_modified,
                "filename": obj.object_name.split("/")[-1],
            }
            for obj in objects
        ]
    except S3Error as e:
        raise StorageError(f"List failed: {e}")
