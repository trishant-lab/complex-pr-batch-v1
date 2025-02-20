import base64
import mimetypes
import os
from pathlib import Path

from opendal import Operator
from loguru import logger

from app.core.settings import AppSettings


def get_opendal_operator(access_key: str, secret_key: str, endpoint: str, bucket_name: str) -> Operator:
    """
    Get OpenDAL operator
    """
    return Operator(
        scheme="s3",
        bucket=bucket_name,
        region="auto",
        endpoint=endpoint,
        access_key_id=access_key,
        secret_access_key=secret_key,
    )


def get_opendal_operator_with_session_token(
    access_key: str, secret_key: str, endpoint: str, session_token: str, bucket_name: str
) -> Operator:
    """
    Get OpenDAL operator with session token
    """
    return Operator(
        scheme="s3",
        bucket=bucket_name,
        region="auto",
        endpoint=endpoint,
        access_key_id=access_key,
        secret_access_key=secret_key,
        session_token=session_token,
    )


def upload_file_to_storage(file_path: str, object_name: str, bucket_name: str, storage_client: Operator) -> None:
    """
    Upload file using OpenDAL
    """
    try:
        with open(file_path, "rb") as f:
            content_type = mimetypes.guess_type(str(file_path))[0] or ""
            storage_client.write(f"{bucket_name}/{object_name}", f.read(), content_type=content_type)
        logger.info(f"uploaded objects to s3 path: {object_name}")
    except Exception as e:
        logger.error(f"failed to upload file to s3 object name: {object_name}, error: {e}")


def download_file_from_storage(object_name: str, file_path: str, storage_client: Operator) -> str | None:
    """
    Download file using OpenDAL
    """
    base_dir: str = file_path.rsplit("/", 1)[0]
    Path(base_dir).mkdir(parents=True, exist_ok=True)
    try:
        data = storage_client.read(object_name)
        with open(file_path, "wb") as f:
            f.write(data)
        logger.info(f"getting objects from s3: {object_name}")
        return object_name
    except Exception as e:
        logger.error(f"failed to get file from s3 object name: {object_name} to file path: {file_path}, error: {e}")
        raise e


def check_file_count(
    storage_client: Operator,
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
        entries = storage_client.scan(path)
        storage_file_count = sum(1 for _ in entries)

        logger.info(f"Bucket {bucket_name}: Local files: {local_file_count} Storage Files: {storage_file_count}")
        if local_file_count != storage_file_count:
            msg = f"File count mismatch for {bucket_name}: {local_file_count} != {storage_file_count}"
            logger.error(msg)
            # raise RuntimeError(msg)  # nosec # NOSONAR
    except Exception as e:
        msg = f"Error checking file count for {bucket_name}: {e}"
        logger.error(msg)
        raise RuntimeError(msg)


def sync_and_verify_files(
    op: Operator,
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
                    with open(str(file_path), "rb") as local_file:
                        content = local_file.read()
                        content_type = mimetypes.guess_type(str(file_path))[0] or ""
                        op.write(key, content, content_type=content_type)
                    local_file_count += 1
                except Exception as e:
                    logger.error(f"Failed to upload {key}: {e}")
                    raise RuntimeError(f"Error uploading {key}: {e}")

        # Verify file count
        check_file_count(
            storage_client=op,
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
