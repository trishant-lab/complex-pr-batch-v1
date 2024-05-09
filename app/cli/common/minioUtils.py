import os
import subprocess
import tempfile
import zipfile
from pathlib import Path

import boto3
from loguru import logger

from app.common import download_file_from_storage, get_storage_client, copy_files_to_s3, get_storage_resource, \
    get_storage_client_for_basic_operations, upload_file_to_storage
from app.core.settings import AppSettings, get_settings


def deploy_ui(environment: str, tenant: str, image_tag: str, domain_name: str, repo_name: str):
    """

    :param environment:
    :param tenant:
    :param image_tag:
    :param domain_name:
    :param repo_name:
    :return:
    """
    config: AppSettings = get_settings()

    if environment == "production":
        dest_dir = f"{tenant}.{domain_name}/"
    else:
        dest_dir = f"{tenant}.{domain_name}/{image_tag}"

    s3_client: boto3.client = get_storage_client(config=config)

    try:
        # Copy file from source to temporary folder
        with tempfile.TemporaryDirectory() as tmp_dir:

            download_file_from_storage(
                object_name=f"{repo_name}/{image_tag}/bundle.zip",
                file_path=f"{tmp_dir}/bundle.zip",
                config=config,
                storage_client=s3_client,
            )
            # Unzip the file
            with zipfile.ZipFile(Path(tmp_dir, "bundle.zip").as_posix(), "r") as zip_ref:
                zip_ref.extractall(os.path.join(tmp_dir, "bundle"))

            # Upload the files to S3
            copy_files_to_s3(
                folder_path=os.path.join(tmp_dir, "bundle", "dist"),
                s3_path=dest_dir,
                config=config,
                bucket_name="static",
            )

    except Exception as e:
        logger.error(f"Failed to deploy UI: {e}")
        raise e