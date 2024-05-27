import subprocess
from loguru import logger


def secret_inject(source_file_path, destination_path):
    """
    Inject secrets from 1Password into a file
    """
    commands = [
        "op", "inject", "--force", "-i", source_file_path, "-o", destination_path
    ]
    process = subprocess.Popen(
        commands, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL
    )
    stdout, stderr = process.communicate(timeout=10)

    if process.returncode != 0:
        output = f"Error: {stderr.decode()}"
        logger.error(output)
        raise Exception(output)

    logger.info(f"Secrets injected into {destination_path}")
    return


class OnePasswordUtil:

    def __init__(self, tenant: str, server_item: str, vault: str) -> None:
        self.tenant = tenant
        self.server_item = server_item
        self.vault = vault

    def create_login_item(self, url: str, username: str, password: str) -> None:
        """
        Create a login item in 1Password
        """
        commands = [
            "op", "item", "create", "--category", "login", f"--title={self.server_item}", "--vault", self.vault,
            "--url", url, f"username={username}", f"password={password}"
        ]
        process = subprocess.Popen(
            commands, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL
        )
        stdout, stderr = process.communicate(timeout=10)

        if process.returncode != 0:
            output = f"Error: {stderr.decode()}"
            logger.error(output)
            raise Exception(output)

        return

    def get_key(self, key: str) -> str:
        """
        Get a key-value pair from a 1Password item
        """
        get_command = [
            "op", "item", "get", self.server_item, "--fields", f"{self.tenant}.{key}", "--vault", self.vault
        ]
        process = subprocess.Popen(
            get_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL
        )
        stdout, stderr = process.communicate(timeout=10)

        if process.returncode != 0:
            output = f"Error: {stderr.decode()}"
            logger.error(output)
            return None

        return stdout.decode().strip()

    def insert_if_not_exists(self, key: str, value: str) -> None:
        """
        Insert a key-value pair into a 1Password item if it does not exist
        """
        get_command = [
            "op", "item", "get", self.server_item, "--fields", f"{self.tenant}.{key}", "--vault", self.vault
        ]
        process = subprocess.Popen(
            get_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL
        )
        stdout, stderr = process.communicate(timeout=10)

        if process.returncode != 0:
            if f'"{self.tenant}.{key}" isn\'t a field in the "{self.server_item}" item' not in stderr.decode():
                output = f"Unexpected Error: {stderr.decode()}"
                logger.error(output)
                raise Exception(output)

            commands = [
                "op", "--vault", self.vault, "item", "edit", self.server_item, f"{self.tenant}.{key}={value}"
            ]
            process = subprocess.Popen(
                commands, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL
            )
            stdout, stderr = process.communicate(timeout=10)

            if process.returncode != 0:
                output = f"Error: {stderr.decode()}"
                logger.error(output)
                raise Exception(output)

        else:
            logger.info(f"{key} already exists in {self.server_item} item")

        return

    def create_or_replace(self, key: str, value: str):
        """
        Create or replace a 1Password item
        """
        commands = [
            "op", "--vault", self.vault, "item", "edit", self.server_item, f"{self.tenant}.{key}={value}"
        ]
        process = subprocess.Popen(
            commands, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL
        )
        stdout, stderr = process.communicate(timeout=10)

        if process.returncode != 0:
            output = f"Error: {stderr.decode()}"
            logger.error(output)
            raise Exception(output)

        return
