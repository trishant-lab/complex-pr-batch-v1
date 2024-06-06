import os
import tempfile
import zipfile
from pathlib import Path

import boto3
from loguru import logger

from app.cli.dexit.dexit import DexitSpec
from app.core.settings import AppSettings, get_settings
from app.s3_utils import get_storage_client, download_file_from_storage, copy_files_to_s3, delete_file_from_storage


def deploy_ui(dexit: DexitSpec):
    """

    :param dexit:
    :return:
    """
    config: AppSettings = get_settings()

    environment: str = config.env
    domain_name: str = config.dexit.domain_name
    repo_name = "dexit-ui"
    tenant = dexit.tenant

    if environment == "production":
        dest_dir = f"{tenant}.{domain_name}/"
    else:
        dest_dir = f"{tenant}.{domain_name}/{dexit.imageTag}"

    s3_client: boto3.client = get_storage_client(config=config)

    try:
        # Copy file from source to temporary folder
        with tempfile.TemporaryDirectory() as tmp_dir:

            download_file_from_storage(
                object_name=f"{repo_name}/{dexit.imageTag}/bundle.zip",
                file_path=f"{tmp_dir}/bundle.zip",
                config=config,
                storage_client=s3_client,
                bucket_name="artifacts",
            )
            # Unzip the file
            with zipfile.ZipFile(Path(tmp_dir, "bundle.zip").as_posix(), "r") as zip_ref:
                zip_ref.extractall(os.path.join(tmp_dir, "bundle"))

            # Upload the files to S3
            copy_files_to_s3(
                input_path=os.path.join(tmp_dir, "bundle", "dist", "admin"),
                output_path=f"{config.s3.rclone_remote}:static/{dest_dir}",
                config=config,
            )

            if environment == "production":
                copy_files_to_s3(
                    input_path=os.path.join(tmp_dir, "bundle", "dist", "admin", "index.html"),
                    output_path=f"{config.s3.rclone_remote}:static/{dest_dir}/custom/index.html",
                    config=config,
                )

    except Exception as e:
        logger.error(f"Failed to deploy UI: {e}")
        raise e


def delete_ui_bundle(dexit: DexitSpec):
    """

    :param dexit
    :return:
    """
    config: AppSettings = get_settings()

    environment: str = config.env
    domain_name: str = config.dexit.domain_name
    tenant = dexit.tenant

    if environment == "production":
        bundle_path = f"{tenant}.{domain_name}/"
    else:
        bundle_path = f"{tenant}.{domain_name}/{dexit.imageTag}"

    delete_file_from_storage(
        object_name=bundle_path,
        config=config,
        bucket_name="static",
    )


class UISetup:
    def __init__(self: "UISetup", dexit: DexitSpec) -> None:
        self.dexit = dexit

    def deploy(self: "UISetup") -> None:
        """
        Deploy UI bundle to S3
        """
        deploy_ui(dexit=self.dexit)

    def delete(self: "UISetup") -> None:
        """
        Delete UI bundle from S3
        """
        delete_ui_bundle(dexit=self.dexit)
