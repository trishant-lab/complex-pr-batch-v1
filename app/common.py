import os
import secrets
import string
from pathlib import Path

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError
from loguru import logger

from app.core.settings import AppSettings


def get_storage_client(config: AppSettings):
    """
    Get s3 client object to connect with buckets
    :param config:
    :return:
    """
    return boto3.client(
        "s3",
        endpoint_url=config.s3_endpoint,
        aws_access_key_id=config.s3_access_key,
        aws_secret_access_key=config.s3_secret_key,
        use_ssl=config.s3_use_ssl,
    )


def generate_password(length):
    all_characters = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(all_characters) for i in range(length))
    return password


def download_file_from_storage(
    object_name: str, file_path: str, config: AppSettings, storage_client: BaseClient = None
):
    """
    Download file from s3 to given local destination file_path
    :param storage_client:
    :param file_path:
    :param object_name:
    :param config:
    :return:
    """
    base_dir: str = file_path.rsplit("/", 1)[0]
    if storage_client:
        client = storage_client
    else:
        client = get_storage_client(config=config)
    Path(base_dir).mkdir(parents=True, exist_ok=True)
    try:
        logger.info(f"getting objects from s3: {object_name}")
        client.download_file(Bucket=config.s3_bucket_name, Key=object_name, Filename=file_path)
        logger.info(f"getting objects from s3: {object_name}")
        return object_name
    except ClientError as e:
        logger.error(f"failed to get file from s3 object name: {object_name} to file path: {file_path}, error: {e}")
        return None


def list_files_in_s3_folder(folder_path: str, config: AppSettings) -> list[str]:
    """
    List all files in the given s3 folder path
    :param folder_path:
    :param config:
    :return:
    """
    client = get_storage_client(config=config)
    try:
        response = client.list_objects_v2(Bucket=config.s3_bucket_name, Prefix=folder_path)
        if "Contents" in response:
            return [obj["Key"] for obj in response["Contents"]]
        return []
    except ClientError as e:
        logger.error(f"failed to list files in s3 folder path: {folder_path}, error: {e}")
        return []


def copy_files_to_s3(folder_path: str, s3_path: str, config: AppSettings) -> None:
    s3_path: str = s3_path if s3_path.endswith("/") else f"{s3_path}/"

    cmd: str = f"rclone copy '{folder_path}' {config.s3_rclone_remote}:'{config.s3_media_bucket_name}/{s3_path}'"
    try:
        os.system(cmd)
        logger.info(f"uploaded objects to s3  path:{s3_path}")
        return None
    except Exception as e:
        logger.info(f"failed to upload objects to s3 path :{s3_path} with exception : {e}")
        raise Exception
