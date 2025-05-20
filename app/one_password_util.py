from loguru import logger

from app.utils.subprocess_execution import run_command


async def secret_inject(source_file_path: str, destination_path: "str") -> None:
    """
    Inject secrets from 1Password into a file
    """
    commands = ["op", "inject", "--force", "-i", source_file_path, "-o", destination_path]

    await run_command(commands)


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
        await run_command(commands)

    async def get_key(self: "OnePasswordUtil", key: str) -> None | str:
        """
        Get a key-value pair from a 1Password item
        """
        try:
            get_command = [
                "op",
                "item",
                "get",
                self.server_item,
                "--fields",
                f"{self.tenant}.{key}",
                "--vault",
                self.vault,
            ]
            key_value, _ = await run_command(get_command)
            return key_value.strip()
        except Exception as e:
            logger.error(f"Error getting key {key} from {self.server_item} in {self.vault}: {e}")
            return None

    async def insert_if_not_exists(self: "OnePasswordUtil", key: str, value: str) -> None:
        """
        Insert a key-value pair into a 1Password item if it does not exist
        """
        get_command = ["op", "item", "get", self.server_item, "--fields", f"{self.tenant}.{key}", "--vault", self.vault]

        _, return_code = await run_command(
            get_command, expected_error=f'"{self.tenant}.{key}" isn\'t a field in the "{self.server_item}" item'
        )

        if return_code != 0:
            commands = ["op", "--vault", self.vault, "item", "edit", self.server_item, f"{self.tenant}.{key}={value}"]
            await run_command(commands)

        else:
            logger.info(f"{key} already exists in {self.server_item} item")

    async def create_or_replace(self: "OnePasswordUtil", key: str, value: str) -> None:
        """
        Create or replace a 1Password item
        """
        commands = ["op", "--vault", self.vault, "item", "edit", self.server_item, f"{self.tenant}.{key}={value}"]

        await run_command(commands)
