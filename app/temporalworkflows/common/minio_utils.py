import os
import subprocess
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

    # s3_client = get_storage_client(config=config)

    with tempfile.TemporaryDirectory() as tmp_dir:
        mc_command = ["mc", "cp", f"integrationminio/artifacts/{repo_name}/{image_tag}/bundle.zip", tmp_dir]  # Todo update this path

        subprocess.Popen(mc_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate(timeout=30)

        unzip_command = ["unzip", "-o", "-qq",  Path(tmp_dir, "bundle.zip").as_posix(), "-d", f"{tmp_dir}/bundle"]

        subprocess.Popen(unzip_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate(timeout=30)

        mirror_command = ["mc", "mirror", "--remove", "--overwrite", f"{tmp_dir}/bundle/dist", f"integrationminio/{dest_dir}"]

        subprocess.Popen(mirror_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate(timeout=30)


    # s3_client = get_storage_client(config=config)
    #
    # try:
    #     # Copy file from source to temporary folder
    #     with tempfile.TemporaryDirectory() as tmp_dir:
    #         download_file_from_storage(
    #             object_name=f"{repo_name}/{image_tag}/bundle.zip",
    #             file_path=f"{tmp_dir}/bundle.zip",
    #             config=config,
    #             storage_client=s3_client,
    #         )
    #
    #         # Unzip the file
    #         with zipfile.ZipFile(Path(tmp_dir, "bundle.zip").as_posix(), "r") as zip_ref:
    #             zip_ref.extractall(tmp_dir)
    #
    #         # Mirror the unzipped content to the destination
    #         copy_files_to_s3(f"{tmp_dir}/bundle/dist", dest_dir, get_settings())
    #
    # except Exception as e:
    #     logger.error(f"Failed to deploy UI: {e}")
    #     raise e
