import io
from pathlib import Path
import uuid
from botocore.client import Config
from botocore.exceptions import ClientError
import boto3
from fastapi import HTTPException, UploadFile

from app.core.config import get_settings

settings = get_settings()


def _client():
    return boto3.client(
        's3',
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(signature_version='s3v4'),
    )


def validate_upload(file: UploadFile, data: bytes) -> None:
    filename = (file.filename or '').strip()
    if not filename:
        raise HTTPException(status_code=400, detail='Missing filename')
    if len(filename) > settings.max_upload_filename_length:
        raise HTTPException(status_code=400, detail='Filename too long')

    extension = filename.split('.')[-1].lower() if '.' in filename else ''
    allowed_exts = {v.strip().lower() for v in settings.allowed_file_extensions.split(',') if v.strip()}
    if extension not in allowed_exts:
        raise HTTPException(status_code=400, detail='Unsupported file extension')

    allowed_types = {v.strip() for v in settings.allowed_mime_types.split(',')}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail='Unsupported file type')

    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(status_code=400, detail='File too large')


def upload_file(user_id: str, file: UploadFile, data: bytes) -> tuple[str, str]:
    extension = (file.filename or '').split('.')[-1].lower()
    key = f'documents/{user_id}/{uuid.uuid4()}.{extension or "bin"}'

    if settings.storage_backend == 'local':
        full_path = _local_path_from_key(key)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
        return 'local', key

    client = _client()
    _ensure_bucket(client, settings.s3_bucket)
    client.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=io.BytesIO(data),
        ContentType=file.content_type,
    )
    return settings.s3_bucket, key


def download_file(bucket: str, key: str) -> bytes:
    if settings.storage_backend == 'local' or bucket == 'local':
        return _local_path_from_key(key).read_bytes()

    client = _client()
    response = client.get_object(Bucket=bucket, Key=key)
    return response['Body'].read()


def _ensure_bucket(client, bucket_name: str) -> None:
    try:
        client.head_bucket(Bucket=bucket_name)
    except ClientError:
        client.create_bucket(Bucket=bucket_name)


def _local_path_from_key(key: str) -> Path:
    root = Path(settings.local_storage_root).resolve()
    target = (root / key).resolve()
    if not str(target).startswith(str(root)):
        raise HTTPException(status_code=400, detail='Invalid file path')
    return target
