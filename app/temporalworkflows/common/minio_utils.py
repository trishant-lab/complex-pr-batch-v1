import os
import tempfile
import zipfile
from pathlib import Path

from loguru import logger

from app.common import download_file_from_storage, get_storage_client, copy_files_to_s3
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
        dest_dir = f"static/{tenant}.{domain_name}/"
    else:
        dest_dir = f"static/{tenant}.{domain_name}/{image_tag}"

    s3_client = get_storage_client(config=config)

    try:
        # Copy file from source to temporary folder
        with tempfile.TemporaryDirectory() as tmp_dir:
            download_file_from_storage(
                f"artifacts/{repo_name}/{image_tag}/bundle.zip",
                f"{tmp_dir}/bundle.zip",
                get_settings(),
                s3_client,
            )

            # Unzip the file
            with zipfile.ZipFile(Path(tmp_dir, "bundle.zip").as_posix(), "r") as zip_ref:
                zip_ref.extractall(tmp_dir)

            # Mirror the unzipped content to the destination
            copy_files_to_s3(f"{tmp_dir}/bundle/dist", dest_dir, get_settings())

    except Exception as e:
        logger.error(f"Failed to deploy UI: {e}")
        raise e
