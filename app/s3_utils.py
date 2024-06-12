from pathlib import Path
from typing import Optional

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError
from loguru import logger
from rclone_python import rclone
from rclone_python.remote_types import RemoteTypes

from app.core.settings import AppSettings


def get_storage_client(config: AppSettings):
    """
    Get s3 client object to connect with buckets
    :param config:
    :return:
    """
    return boto3.client(
        "s3",
        endpoint_url=config.s3.endpoint,
        aws_access_key_id=config.s3.access_key,
        aws_secret_access_key=config.s3.secret_key,
        use_ssl=config.s3.use_ssl,
    )


def get_storage_resource(config: AppSettings):
    """
    Get s3 resource object to connect with buckets
    :param config:
    :return:
    """
    return boto3.resource(
        "s3",
        endpoint_url=config.s3.endpoint,
        aws_access_key_id=config.s3.access_key,
        aws_secret_access_key=config.s3.secret_key,
        use_ssl=config.s3.use_ssl,
    )


def download_file_from_storage(
    object_name: str, file_path: str, config: AppSettings, bucket_name: str, storage_client: BaseClient = None
):
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
    if storage_client:
        client = storage_client
    else:
        client = get_storage_client(config=config)
    Path(base_dir).mkdir(parents=True, exist_ok=True)
    try:
        client.download_file(Bucket=bucket_name, Key=object_name, Filename=file_path)
        logger.info(f"getting objects from s3: {object_name}")
        return object_name
    except ClientError as e:
        logger.error(f"failed to get file from s3 object name: {object_name} to file path: {file_path}, error: {e}")
        return None


def upload_file_to_storage(
    object_name: str,
    file_path,
    config: AppSettings,
    content_type: Optional[str] = None,
    s3_bucket_name: Optional[str] = None,
    storage_client: BaseClient = None,
):
    """
    Upload file to s3 using local file path
    :return:
    """
    if storage_client:
        client = storage_client
    else:
        client = get_storage_client(config=config)
    try:
        client.upload_file(
            Bucket=s3_bucket_name if s3_bucket_name else config.s3_media_bucket_name,
            Key=object_name,
            Filename=file_path,
            ExtraArgs={"ContentType": content_type} if content_type else None,
        )

        logger.info(f"added objects to cloud: {object_name}")
    except ClientError:
        logger.error(f"failed to add objects to cloud: {object_name} ")
        return "failed"
    return "success"


def create_rclone_remote(config: AppSettings) -> None:
    try:
        rclone.create_remote(
            remote_name=config.s3.rclone_remote,
            remote_type=RemoteTypes.s3,
            client_id=config.s3.access_key,
            client_secret=config.s3.secret_key,
            provider="Cloudflare",
            endpoint=config.s3.endpoint,
        )
    except Exception as e:
        logger.error(e)


def copy_files_to_s3(input_path: str, output_path: str, config: AppSettings) -> None:

    create_rclone_remote(config)
    rclone.copy(
        in_path=input_path,
        out_path=output_path,
    )
    logger.info(f"uploaded objects to s3  path:{output_path}")


def copy_files_from_s3(folder_path: str, s3_path: str, bucket_name: str, config: AppSettings) -> None:
    # s3_path: str = s3_path if s3_path.endswith("/") else f"{s3_path}/"
    logger.info(f"downloading objects from s3  path:{s3_path}")

    create_rclone_remote(config)
    rclone.copy(
        in_path=f"{config.s3.rclone_remote}:{bucket_name}/{s3_path}",
        out_path=folder_path,
    )
    logger.info(f"downloaded objects from s3  path:{s3_path}")


def delete_file_from_storage(object_name: str, bucket_name: str, config: AppSettings) -> None:
    create_rclone_remote(config)
    rclone.delete(f"{config.s3.rclone_remote}:{bucket_name}/{object_name}/")
    logger.info(f"deleted object from s3: {object_name}")