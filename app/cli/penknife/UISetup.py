import os
import tempfile
import zipfile
from pathlib import Path

import boto3
from loguru import logger

from app.cli.penknife.models.penknifespec import PenknifeSpec
from app.cli.temporal.core.log import log_info
from app.core.settings import AppSettings, get_settings
from app.s3_utils import get_storage_client, download_file_from_storage, copy_files_to_s3, delete_file_from_storage


def deploy_ui(penknife: PenknifeSpec) -> None:
    """

    :param penknife:
    :return:
    """
    config: AppSettings = get_settings()

    environment: str = config.env
    domain_name: str = config.penknife.domain_name
    repo_name = "penknife-ui"
    tenant = penknife.tenant
    image_tag = "production" if environment == "production" else "sprint"

    if environment == "production":
        dest_dir = f"{tenant}.{domain_name}/"
    else:
        dest_dir = f"{tenant}.{domain_name}/{image_tag}"

    s3_client: boto3.client = get_storage_client(
        config=config, access_key=config.s3.access_key, secret_key=config.s3.secret_key
    )

    try:
        # Copy file from source to temporary folder
        with tempfile.TemporaryDirectory() as tmp_dir:
            download_file_from_storage(
                object_name=f"{repo_name}/{image_tag}/bundle.zip",
                file_path=f"{tmp_dir}/bundle.zip",
                storage_client=s3_client,
                bucket_name="artifacts",
            )
            # Unzip the file
            with zipfile.ZipFile(Path(tmp_dir, "bundle.zip").as_posix(), "r") as zip_ref:
                zip_ref.extractall(os.path.join(tmp_dir, "bundle"))

            # Upload the files to S3
            copy_files_to_s3(
                input_path=os.path.join(tmp_dir, "bundle", "dist", "admin"),
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


def delete_ui_bundle(penknife: PenknifeSpec) -> None:
    """

    :param penknife
    :return:
    """
    config: AppSettings = get_settings()

    environment: str = config.env
    domain_name: str = config.penknife.domain_name
    tenant = penknife.tenant
    image_tag = "production" if environment == "production" else "sprint"

    if environment == "production":
        bundle_path = f"{tenant}.{domain_name}/"
    else:
        bundle_path = f"{tenant}.{domain_name}/{image_tag}"

    delete_file_from_storage(
        object_name=bundle_path,
        config=config,
        bucket_name="static",
    )


class UISetup:
    def __init__(self: "UISetup", penknife: PenknifeSpec) -> None:
        self.penknife = penknife

    def deploy(self: "UISetup") -> None:
        """
        Deploy UI bundle to S3
        """
        deploy_ui(penknife=self.penknife)

    def delete(self: "UISetup") -> None:
        """
        Delete UI bundle from S3
        """
        delete_ui_bundle(penknife=self.penknife)
