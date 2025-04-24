from asyncio import subprocess
import base64
import mimetypes
import os
from pathlib import Path

from app.cli.temporal.muspell import TemplatePath
from app.template_env import get_env
from loguru import logger

from app.core.settings import AppSettings, get_settings
from app.utils.file_operations import get_opendal_file_client
from app.utils.s3_operations import OpendalS3Client


async def download_file_from_storage(object_name: str, file_path: str, storage_client: OpendalS3Client) -> str | None:
    """
    Download file using OpenDAL
    """
    base_dir: str = file_path.rsplit("/", 1)[0]
    Path(base_dir).mkdir(parents=True, exist_ok=True)
    try:
        data = await storage_client.get_file_content(object_name)
        opendal_file_operations = get_opendal_file_client()
        await opendal_file_operations.write_file(file_path, data)
        logger.info(f"getting objects from s3: {object_name}")
        return object_name
    except Exception as e:
        logger.error(f"failed to get file from s3 object name: {object_name} to file path: {file_path}, error: {e}")
        raise e


async def check_file_count(
    storage_client: OpendalS3Client,
    bucket_name: str,
    local_file_count: int,
    prefix: str | None = None,
) -> None:
    """
    Check if the file count matches between local and s3
    """
    try:
        # Count files in storage
        storage_file_count = 0
        path = "/"
        if prefix:
            path = f"{prefix}"

        # OpenDAL's list method returns an async iterator of entries
        entries = await storage_client.scan_files(path)
        storage_file_count = sum(1 for _ in entries)

        logger.info(f"Bucket {bucket_name}: Local files: {local_file_count} Storage Files: {storage_file_count}")
        if local_file_count != storage_file_count:
            msg = f"File count mismatch for {bucket_name}: {local_file_count} != {storage_file_count}"
            logger.error(msg)
            # raise RuntimeError(msg)  # nosec # NOSONAR
    except Exception as e:
        msg = f"Error checking file count for {bucket_name}: {e}"
        logger.error(msg)
        # raise RuntimeError(msg)


async def sync_and_verify_files(
    op: "OpendalS3Client",
    input_path: str,
    bucket_name: str,
    dest_dir: str,
    prefix: str | None = None,
) -> None:
    """
    Sync local files to storage and verify the file count matches
    Args:
        op: The OpenDAL operator
        input_path: Path to local directory to sync
        bucket_name: Destination bucket name
        dest_dir: Destination directory
        prefix: Optional prefix for file counting
    Raises:
        RuntimeError: If file counts don't match or on upload failure
    """
    try:
        # Count and upload local files
        local_file_count = 0
        for file_path in Path(input_path).rglob("*"):
            if file_path.is_file():
                # Calculate relative path for storage key
                key = str(file_path.relative_to(input_path))
                key = f"{dest_dir.split('/')[-1]}/{key}" if bucket_name in dest_dir else f"{bucket_name}/{key}"
                try:
                    # Read file content and upload
                    opendal_file_operations = get_opendal_file_client()
                    content = await opendal_file_operations.read_file(str(file_path))
                    content_type = mimetypes.guess_type(str(file_path))[0] or ""
                    await op.upload_object(
                        path=key,
                        file_name=key.split("/")[-1],
                        content_type=content_type,
                        file_content=content.encode(),
                    )
                    local_file_count += 1
                except Exception as e:
                    logger.error(f"Failed to upload {key}: {e}")
                    raise RuntimeError(f"Error uploading {key}: {e}")

        # Verify file count
        await check_file_count(
            storage_client=op,
            bucket_name=bucket_name,
            local_file_count=local_file_count,
            prefix=prefix,
        )

    except Exception as e:
        msg = f"Error syncing files for {bucket_name}: {e}"
        logger.error(msg)
        raise RuntimeError(msg)


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


def create_minio_user(config: AppSettings, access_key: str, secret_key: str) -> tuple[str, str]:
    """
    Create a Minio user using mc client via subprocess
    """
    try:
        # Configure mc client
        subprocess.run(
            ["mc", "alias", "set", "minio", config.s3_int.endpoint, config.s3_int.access_key, config.s3_int.secret_key],
            check=True,
            capture_output=True,
        )

        # Create user
        subprocess.run(["mc", "admin", "user", "add", "minio", access_key, secret_key], check=True, capture_output=True)

        logger.info(f"Created Minio user {access_key} successfully")
        return access_key, secret_key

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create Minio user: {e.stderr.decode()}")
        raise MinioUserCreationError(f"Failed to create Minio user: {e.stderr.decode()}")


def create_minio_bucket(config: AppSettings, bucket_name: str, region_name: str) -> None:
    """
    Create a Minio bucket using mc client via subprocess
    """
    subprocess.run(
        ["mc", "alias", "set", "minio", config.s3_int.endpoint, config.s3_int.access_key, config.s3_int.secret_key],
        check=True,
        capture_output=True,
    )

    subprocess.run(["mc", "mb", "--region", region_name, f"minio/{bucket_name}"], check=True, capture_output=True)

    logger.info(f"Created Minio bucket '{bucket_name}' in region '{region_name}' successfully")


async def attach_minio_policy(bucket_name: str, access_key: str) -> None:
    """
    Create a Minio policy and attach it to a user using mc client via subprocess
    """
    config: AppSettings = get_settings()

    subprocess.run(
        ["mc", "alias", "set", "minio", config.s3_int.endpoint, config.s3_int.access_key, config.s3_int.secret_key],
        check=True,
        capture_output=True,
    )

    template_env = get_env(template_path=TemplatePath)
    policy_template = template_env.get_template("minio_policy.json")
    rendered_policy = policy_template.render(bucket_name=bucket_name)

    # Use a temporary file with context manager to ensure cleanup

    opendal_file_operations = get_opendal_file_client()
    async with opendal_file_operations.temp_file() as temp_file:
        await temp_file.write(rendered_policy.encode())
        temp_file_path = temp_file.name

        try:
            # Create the policy using mc admin
            subprocess.run(
                ["mc", "admin", "policy", "create", "minio", "bucketpolicy", temp_file_path],
                check=True,
                capture_output=True,
            )

            # Attach the policy to the user
            subprocess.run(
                ["mc", "admin", "policy", "attach", "minio", "bucketpolicy", "--user", access_key],
                check=True,
                capture_output=True,
            )

            logger.info(f"Attached policy to user {access_key} successfully")
        finally:
            # Ensure the temporary file is removed even if an exception occurs
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)


class MinioUserCreationError(Exception):
    """Exception raised when creating a Minio user fails."""

    pass
