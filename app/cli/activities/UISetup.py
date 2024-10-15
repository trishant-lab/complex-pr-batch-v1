import os
import tempfile
import zipfile
from pathlib import Path

import boto3
from loguru import logger

from app.cli.temporal.core.log import log_info
from app.core.settings import AppSettings, get_settings
from app.s3_utils import get_storage_client, download_file_from_storage, copy_files_to_s3, delete_file_from_storage


def deploy_ui(src_object_name: str, dest_dir: str, product_name: str | None = None) -> None:
    """

    :return:
    """
    config: AppSettings = get_settings()

    environment: str = config.env

    s3_int_client: boto3.client = get_storage_client(
        config=config,
        access_key=config.s3_int.access_key,
        secret_key=config.s3_int.secret_key,
        endpoint=config.s3_int.endpoint,
    )

    try:
        # Copy file from source to temporary folder
        with tempfile.TemporaryDirectory() as tmp_dir:
            download_file_from_storage(
                object_name=src_object_name,
                file_path=f"{tmp_dir}/bundle.zip",
                storage_client=s3_int_client,
                bucket_name="artifacts",
            )
            # Unzip the file
            with zipfile.ZipFile(Path(tmp_dir, "bundle.zip").as_posix(), "r") as zip_ref:
                zip_ref.extractall(os.path.join(tmp_dir, "bundle"))

            input_path = os.path.join(tmp_dir, "bundle", "dist", "admin")

            if product_name and product_name.lower() == "penknife":
                input_path = os.path.join(tmp_dir, "bundle", "dist")

            # Upload the files to S3
            copy_files_to_s3(
                input_path=input_path,
                output_path=f"{config.s3.rclone_remote}/static/{dest_dir}",
                config=config,
            )

            if environment == "production":
                copy_files_to_s3(
                    input_path=os.path.join(tmp_dir, "bundle", "dist", "admin", "index.html"),
                    output_path=f"{config.s3.rclone_remote}/static/{dest_dir}/custom/index.html",
                    config=config,
                )

        log_info(f"UI deployed successfully to {dest_dir}")

    except Exception as e:
        logger.error(f"Failed to deploy UI: {e}")
        raise e


def delete_ui_bundle(dest_dir: str) -> None:
    """

    :param tenant
    :param domain_name
    :return:
    """
    config: AppSettings = get_settings()

    delete_file_from_storage(
        object_name=dest_dir,
        config=config,
        bucket_name="static",
    )


class UISetup:
    def __init__(self: "UISetup", src_object_name: str, dest_dir: str, product_name: str | None = None) -> None:
        self.src_object_name = src_object_name
        self.dest_dir = dest_dir
        self.product_name = product_name

    def deploy(self: "UISetup") -> None:
        """
        Deploy UI bundle to S3
        """
        deploy_ui(src_object_name=self.src_object_name, dest_dir=self.dest_dir, product_name=self.product_name)

    def delete(self: "UISetup") -> None:
        """
        Delete UI bundle from S3
        """
        delete_ui_bundle(dest_dir=self.dest_dir)
