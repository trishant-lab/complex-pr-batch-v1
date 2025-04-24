import asyncio
from loguru import logger


async def secret_inject(source_file_path: str, destination_path: "str") -> None:
    """
    Inject secrets from 1Password into a file
    """
    commands = ["op", "inject", "--force", "-i", source_file_path, "-o", destination_path]

    process = await asyncio.create_subprocess_exec(
        *commands,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.DEVNULL,
    )

    _stdout, stderr = await process.communicate()

    if process.returncode != 0:
        output = f"Error: {stderr.decode()}"
        logger.error(output)
        raise RuntimeError(output)

    logger.info(f"Secrets injected into {destination_path}")


class OnePasswordUtil:
    def __init__(self: "OnePasswordUtil", tenant: str, server_item: str, vault: str) -> None:
        self.tenant = tenant
        self.server_item = server_item
        self.vault = vault

    async def create_login_item(self: "OnePasswordUtil", url: str, username: str, password: str) -> None:
        """
        Create a login item in 1Password
        """
        commands = [
            "op",
            "item",
            "create",
            "--category",
            "login",
            f"--title={self.server_item}",
            "--vault",
            self.vault,
            "--url",
            url,
            f"username={username}",
            f"password={password}",
        ]
        process = await asyncio.create_subprocess_exec(
            *commands,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
        )
        _stdout, stderr = await process.communicate()

        if process.returncode != 0:
            output = f"Error: {stderr.decode()}"
            logger.error(output)
            raise RuntimeError(output)

    async def get_key(self: "OnePasswordUtil", key: str) -> None | str:
        """
        Get a key-value pair from a 1Password item
        """
        get_command = ["op", "item", "get", self.server_item, "--fields", f"{self.tenant}.{key}", "--vault", self.vault]
        process = await asyncio.create_subprocess_exec(
            *get_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            output = f"Error: {stderr.decode()}"
            logger.error(output)
            return None

        return stdout.decode().strip()

    async def insert_if_not_exists(self: "OnePasswordUtil", key: str, value: str) -> None:
        """
        Insert a key-value pair into a 1Password item if it does not exist
        """
        get_command = ["op", "item", "get", self.server_item, "--fields", f"{self.tenant}.{key}", "--vault", self.vault]
        process = await asyncio.create_subprocess_exec(
            *get_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
        )
        _stdout, stderr = await process.communicate()

        if process.returncode != 0:
            if f'"{self.tenant}.{key}" isn\'t a field in the "{self.server_item}" item' not in stderr.decode():
                output = f"Unexpected Error: {stderr.decode()}"
                logger.error(output)
                raise RuntimeError(output)

            commands = ["op", "--vault", self.vault, "item", "edit", self.server_item, f"{self.tenant}.{key}={value}"]
            process = await asyncio.create_subprocess_exec(
                *commands,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,
            )
            _stdout, stderr = await process.communicate()

            if process.returncode != 0:
                output = f"Error: {stderr.decode()}"
                logger.error(output)
                raise RuntimeError(output)

        else:
            logger.info(f"{key} already exists in {self.server_item} item")

    async def create_or_replace(self: "OnePasswordUtil", key: str, value: str) -> None:
        """
        Create or replace a 1Password item
        """
        commands = ["op", "--vault", self.vault, "item", "edit", self.server_item, f"{self.tenant}.{key}={value}"]
        process = await asyncio.create_subprocess_exec(
            *commands,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
        )
        _stdout, stderr = await process.communicate()

        if process.returncode != 0:
            output = f"Error: {stderr.decode()}"
            logger.error(output)
            raise RuntimeError(output)
