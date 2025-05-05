from collections.abc import AsyncGenerator
import opendal


class OpendalS3Client:
    def __init__(
        self: "OpendalS3Client",
        access_key: str,
        secret_key: str,
        endpoint: str,
        bucket_name: str,
        region: str,
        session_token: str | None = None,
    ) -> None:
        """
        Initialize the CloudflareR2 class with Cloudflare R2 credentials from app config.

        This constructor sets up an OpenDAL AsyncOperator with the necessary S3-compatible
        configuration for Cloudflare R2 access.

        Note:
            The credentials and configuration are automatically loaded from APP_CONFIG.cloudflare_r2

        """
        if session_token:
            self.client = opendal.AsyncOperator(
                scheme="s3",
                region=region,
                endpoint=endpoint,
                bucket=bucket_name,
                access_key_id=access_key,
                secret_access_key=secret_key,
                session_token=session_token,
            )
        else:
            self.client = opendal.AsyncOperator(
                scheme="s3",
                region=region,
                endpoint=endpoint,
                bucket=bucket_name,
                access_key_id=access_key,
                secret_access_key=secret_key,
            )

    async def upload_object(
        self: "OpendalS3Client", path: str, file_name: str, content_type: str, file_content: bytes
    ) -> None:
        """
        Upload an object to Cloudflare R2 using a blob ID and file name.

        Args:
            path (str): The path of the file to be uploaded.
            file_name (str): The name of the file to be uploaded.
            content_type (str): The MIME type of the file.
            file_content (bytes): The binary content of the file to be uploaded.

        Returns:
            None

        """
        content_disposition = f'attachment; filename="{file_name}"'
        await self.client.write(
            path=path, bs=file_content, content_type=content_type, content_disposition=content_disposition
        )

    async def replace_object(self: "OpendalS3Client", path: str, file_content: bytes) -> None:
        """
        Replace the content of an existing object in Cloudflare R2.

        Args:
            path (str): The path of the file to be replaced.
            file_content (bytes): The new binary content to replace the existing file.

        Returns:
            None

        """
        file_stat = await self.client.stat(path=path)
        await self.client.write(
            path=path,
            bs=file_content,
            content_type=file_stat.content_type,
            content_disposition=file_stat.content_disposition,
        )

    async def get_file_content(self: "OpendalS3Client", path: str) -> bytes:
        """
        Retrieve file contents by blob ID.

        Args:
            path (str): The path of the file to be retrieved.

        Returns:
            bytes: The binary contents of the file associated with the blob ID.

        """
        return await self.client.read(path=path)

    async def delete_file(self: "OpendalS3Client", path: str) -> None:
        """
        Delete a file from Cloudflare R2 using its blob ID.

        Args:
            path (str): The path of the file to be deleted.

        Returns:
            None

        """
        await self.client.delete(path=path)

    async def get_pre_signed_read_url(self: "OpendalS3Client", path: str, expiry_time: int = 3600) -> str:
        """
        Generate a pre-signed URL for temporary read access to a file using its blob ID.

        Args:
            path (str): The path of the file to be retrieved.
            expiry_time (int, optional): The time in seconds for which the URL is valid. Defaults to 3600.

        Returns:
            str: A URL that provides temporary read access to the file.

        """
        res = await self.client.presign_read(path=path, expire_second=expiry_time)
        return res.url

    async def scan_files(self, path: str) -> AsyncGenerator[opendal.Entry, None]:
        """
        Scan all files in a directory
        """
        lister = await self.client.scan(path)
        async for entry in lister:
            yield entry


def get_s3_client(
    access_key: str,
    secret_key: str,
    endpoint: str,
    bucket_name: str,
    region: str = "auto",
    session_token: str | None = None,
) -> OpendalS3Client:
    """
    Create and return a singleton instance of the OpendalS3Client.

    Returns:
        OpendalS3Client: A singleton instance of the OpendalS3Client.

    """
    return OpendalS3Client(
        access_key=access_key,
        secret_key=secret_key,
        endpoint=endpoint,
        bucket_name=bucket_name,
        region=region,
        session_token=session_token,
    )
