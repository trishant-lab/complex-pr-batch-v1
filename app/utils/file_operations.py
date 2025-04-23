from functools import lru_cache
import opendal


class OpendalFileOperations:
    def __init__(self: "OpendalFileOperations") -> None:
        """
        Initialize the OpendalFileOperations class
        """
        self.client = opendal.AsyncOperator(
            scheme="fs",
            root="/",
        )

    async def read_file(self, file_path: str) -> str:
        """
        Read a file from the local file system
        """
        async with await self.client.open(file_path, mode="rb") as file:
            content = await file.read()
            return content.decode() if isinstance(content, bytes) else content

    async def write_file(self, file_path: str, content: str) -> None:
        """
        Write a file to the local file system
        """
        async with await self.client.open(file_path, "wb") as file:
            await file.write(content.encode())

    async def list_files(self, path: str) -> list[str]:
        """
        List all files in a directory
        """
        return await self.client.list(path)

    async def delete_file(self, file_path: str) -> None:
        """
        Delete a file from the local file system
        """
        await self.client.delete(file_path)


@lru_cache
def get_opendal_file_client() -> OpendalFileOperations:
    """
    Create and return a singleton instance of the OpendalFileOperations.

    Returns:
        OpendalFileOperations: A singleton instance of the OpendalFileOperations.

    """
    return OpendalFileOperations()
