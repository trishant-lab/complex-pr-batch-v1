import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import lru_cache

import opendal
from uuid_extensions import uuid7str


class OpendalFileOperations:
    def __init__(self: "OpendalFileOperations") -> None:
        """
        Initialize the OpendalFileOperations class
        """
        self.client = opendal.Operator(scheme="fs", root="/")
        self.a_client = opendal.AsyncOperator(scheme="fs", root="/")
        self.tempdir_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "temp"))
        os.makedirs(self.tempdir_root, exist_ok=True)
        self.tempdir_client = opendal.AsyncOperator(scheme="fs", root=self.tempdir_root)

    def read_file_sync(self, file_path: str, mode: str = "rb") -> bytes:
        """
        Read a file from the local file system using client
        """
        with self.client.open(file_path, mode) as file:
            return file.read()

    async def read_file(self, file_path: str, mode: str = "rb") -> bytes:
        """
        Read a file from the local file system using a_client
        """
        async with await self.a_client.open(file_path, mode) as file:
            return await file.read()

    async def write_file(self, file_path: str, content: bytes | str, mode: str = "wb") -> None:
        """
        Write a file to the local file system using a_client
        """
        # This uses self.a_client rooted at /
        async with await self.a_client.open(file_path, mode) as file:
            await file.write(content) if isinstance(content, bytes) else await file.write(content.encode())

    async def list_files(self, path: str) -> list[str]:
        """
        List all files in a directory
        """
        # This uses self.a_client rooted at /
        # Consider if this should use tempdir_client for relative paths
        if not await self.a_client.exists(path):
            raise NotADirectoryError(f"File {path} does not exist")
        return await self.a_client.list(path)

    async def delete_file(self, file_path: str) -> None:
        """
        Delete a file from the local file system using a_client
        """
        # This uses self.a_client rooted at /
        # Consider if this should use tempdir_client for relative paths
        if not await self.a_client.exists(file_path):
            return
        await self.a_client.delete(file_path)

    @asynccontextmanager
    async def temp_dir(self, dir_prefix: str | None = None) -> AsyncGenerator[str, None]:
        """
        Create a temporary directory relative to tempdir_client's root.
        Yields a path relative to tempdir_root.
        """
        uuid_v7 = uuid7str()
        _prefix = f"{dir_prefix}_" if dir_prefix else ""
        # temp_dir is relative to tempdir_client's root
        temp_dir_relative = f"{_prefix}{uuid_v7}/"
        # Create dir using tempdir_client
        await self.tempdir_client.create_dir(temp_dir_relative)
        try:
            yield temp_dir_relative  # Yield the relative path
        finally:
            # Clean up using tempdir_client and relative path
            # scan includes the directory itself, need to handle files first
            async for entry in await self.tempdir_client.scan(temp_dir_relative):
                # Check the metadata mode to determine if it's a file
                await self.tempdir_client.delete(entry.path)

            # Delete the directory itself using tempdir_client
            # Ensure path ends with / for opendal dir deletion
            dir_path_to_delete = temp_dir_relative if temp_dir_relative.endswith("/") else f"{temp_dir_relative}/"
            await self.tempdir_client.remove_all(dir_path_to_delete)

    @asynccontextmanager
    async def temp_file(
        self,
        mode: str = "wb",
        dir_prefix: str | None = None,
    ) -> AsyncGenerator[opendal.AsyncFile, None]:
        """
        Create a temporary file within tempdir_client's root.
        Yields an opendal.AsyncFile object managed by tempdir_client.
        """
        uuid_v7 = uuid7str()
        _prefix = f"{dir_prefix}_" if dir_prefix else ""
        # file_path is relative to tempdir_client's root
        file_path_relative = f"{_prefix}{uuid_v7}"
        try:
            # Open using tempdir_client
            async with await self.tempdir_client.open(file_path_relative, mode) as file_obj:
                yield file_obj
        finally:
            # Delete using tempdir_client
            # Check existence before deleting
            if await self.tempdir_client.exists(file_path_relative):
                await self.tempdir_client.delete(file_path_relative)


@lru_cache
def get_opendal_file_client() -> OpendalFileOperations:
    """
    Create and return a singleton instance of the OpendalFileOperations.

    Returns:
        OpendalFileOperations: A singleton instance of the OpendalFileOperations.

    """
    return OpendalFileOperations()
