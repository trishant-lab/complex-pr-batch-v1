import base64
import mimetypes
import os
from pathlib import Path

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError
from loguru import logger

from app.core.settings import AppSettings


def get_r2_storage_client(config: AppSettings) -> boto3.client:
    """
    Get s3 client object to connect with buckets
    :param config:
    :return:
    """
    return boto3.client(
        "s3",
        endpoint_url=config.r2.endpoint,
        aws_access_key_id=config.r2.access_key,
        aws_secret_access_key=config.r2.secret_key,
        use_ssl=config.r2.use_ssl,
    )


def get_storage_client(config: AppSettings, access_key: str, secret_key: str, endpoint: str) -> boto3.client:
    """
    Get s3 client object to connect with buckets
    :param access_key:
    :param secret_key:
    :param endpoint:
    :param config:
    :return:
    """
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        use_ssl=config.s3.use_ssl,
    )


def get_storage_client_with_session_token(
    config: AppSettings, access_key: str, secret_key: str, endpoint: str, session_token: str
) -> boto3.client:
    """
    Get s3 client object to connect with buckets
    :param access_key:
    :param secret_key:
    :param endpoint:
    :param config:
    :return:
    """
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        aws_session_token=session_token,
        use_ssl=config.s3.use_ssl,
    )


def upload_file_to_storage(file_path: str, object_name: str, bucket_name: str, storage_client: BaseClient) -> None:
    """
    Upload file to s3
    """
    try:
        storage_client.upload_file(Filename=file_path, Bucket=bucket_name, Key=object_name)
        logger.info(f"uploaded objects to s3 path: {object_name}")
    except ClientError as e:
        logger.error(f"failed to upload file to s3 object name: {object_name}, error: {e}")


def download_file_from_storage(
    object_name: str, file_path: str, bucket_name: str, storage_client: BaseClient
) -> str | None:
    """
    Download file from s3 to given local destination file_path
    :param storage_client:
    :param file_path:
    :param object_name:
    :param config:
    :param bucket_name:
    :return:
    """
    base_dir: str = file_path.rsplit("/", 1)[0]
    Path(base_dir).mkdir(parents=True, exist_ok=True)
    try:
        storage_client.download_file(Bucket=bucket_name, Key=object_name, Filename=file_path)
        logger.info(f"getting objects from s3: {object_name}")
        return object_name
    except ClientError as e:
        logger.error(f"failed to get file from s3 object name: {object_name} to file path: {file_path}, error: {e}")
        return None


def check_file_count(
    storage_client: BaseClient,
    bucket_name: str,
    local_file_count: int,
    prefix: str | None = None,
) -> None:
    """
    Check if the file count matches between local and s3
    """
    # Count files in S3
    s3_file_count = 0
    paginator = storage_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket_name):
        # Only count files from the specific path we uploaded from
        if "Contents" in page and prefix:
            s3_file_count += sum(1 for item in page["Contents"] if item["Key"].startswith(prefix))
        else:
            s3_file_count += len(page.get("Contents", []))

    logger.info(f"Bucket {bucket_name}: Local files: {local_file_count} S3 Files: {s3_file_count}")
    if local_file_count != s3_file_count:
        msg = f"File count mismatch for {bucket_name}: {local_file_count} != {s3_file_count}"
        logger.error(msg)
        raise RuntimeError(msg)


def sync_and_verify_files(
    storage_client: BaseClient,
    input_path: str,
    bucket_name: str,
    dest_dir: str,
    prefix: str | None = None,
) -> None:
    """
    Sync local files to S3/R2 and verify the file count matches
    Args:
        storage_client: The S3/R2 client
        local_path: Path to local directory to sync
        bucket_name: Destination bucket name
    Raises:
        RuntimeError: If file counts don't match or on upload failure
    """
    try:
        # Count and upload local files
        local_file_count = 0
        for file_path in Path(input_path).rglob("*"):
            if file_path.is_file():
                # Calculate relative path for S3 key
                key = str(file_path.relative_to(input_path))
                key = f"{dest_dir.split('/')[-1]}/{key}" if bucket_name in dest_dir else f"{bucket_name}/{key}"
                try:
                    content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
                    storage_client.upload_file(
                        Filename=str(file_path), Bucket=bucket_name, Key=key, ExtraArgs={"ContentType": content_type}
                    )
                    local_file_count += 1
                except ClientError as e:
                    logger.error(f"Failed to upload {key}: {e}")
                    raise RuntimeError(f"Error uploading {key}: {e}")

        # Count files in S3
        check_file_count(
            storage_client=storage_client,
            bucket_name=bucket_name,
            local_file_count=local_file_count,
            prefix=prefix,
        )

    except Exception as e:
        msg = f"Error syncing files for {bucket_name}: {e}"
        logger.error(msg)
        raise RuntimeError(msg)


def mirror_files_to_cloudflare(
    tenant: str, input_path: str, output_path: str, endpoint: str, access_key: str, secret_key: str, session_token: str
) -> None:
    """
    Copy objects from local to cloudflare
    """
    session_token = base64.b64decode(session_token).decode("utf-8")
    url = endpoint.split("://")[1]
    command = (
        f"MC_HOST_launchpad_{tenant}=https://{access_key}:{secret_key}:{session_token}@{url} "
        f"mc mirror --remove --overwrite {input_path} launchpad_{tenant}/{output_path}"
    )
    os.system(command)  # nosec


def copy_files_to_cloudflare(
    tenant: str, input_path: str, output_path: str, endpoint: str, access_key: str, secret_key: str, session_token: str
) -> None:
    """
    Copy objects from local to cloudflare
    """
    session_token = base64.b64decode(session_token).decode("utf-8")
    url = endpoint.split("://")[1]
    command = (
        f"MC_HOST_launchpad_{tenant}=https://{access_key}:{secret_key}:{session_token}@{url} "
        f"mc cp -r {input_path} launchpad_{tenant}/{output_path}"
    )
    os.system(command)  # nosec


def delete_files_from_cloudflare(
    tenant: str, input_path: str, endpoint: str, access_key: str, secret_key: str, session_token: str
) -> None:
    """
    Delete objects from cloudflare
    """
    session_token = base64.b64decode(session_token).decode("utf-8")
    url = endpoint.split("://")[1]
    command = (
        f"MC_HOST_launchpad_{tenant}=https://{access_key}:{secret_key}:{session_token}@{url} "
        f"mc rm --force --recursive launchpad_{tenant}/{input_path}"
    )
    os.system(command)  # nosec


def copy_files_to_cloudflare_with_exclude(
    tenant: str,
    input_path: str,
    output_path: str,
    exclude_pattern: str,
    endpoint: str,
    access_key: str,
    secret_key: str,
    session_token: str,
) -> None:
    """
    Copy objects from local to cloudflare
    """
    session_token = base64.b64decode(session_token).decode("utf-8")
    url = endpoint.split("://")[1]
    command = (
        f"MC_HOST_launchpad_{tenant}=https://{access_key}:{secret_key}:{session_token}@{url} "
        f'mc mirror --remove --overwrite --exclude "{exclude_pattern}" {input_path} launchpad_{tenant}/{output_path}'
    )
    os.system(command)  # nosec


def copy_files_to_s3(
    input_path: str,
    output_path: str,
    config: AppSettings,
) -> None:
    """
    Copy files to s3
    """
    os.system(f"mc alias set launchpad {config.r2.endpoint} {config.r2.access_key} {config.r2.secret_key}")  # nosec
    os.system(f"mc copy {input_path} launchpad/{output_path}")  # nosec
