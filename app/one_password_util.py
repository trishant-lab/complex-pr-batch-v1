import json
import os
import re
from typing import Final

import aiofiles
from loguru import logger

from app.utils.subprocess_execution import run_command


async def secret_inject(source_file_path: str, destination_path: "str") -> None:
    """
    Inject secrets from 1Password into a file
    """
    commands = ["op", "inject", "--force", "-i", source_file_path, "-o", destination_path]

    await run_command(commands)


# Matches `{{ op://VAULT/ITEM/SECTION/FIELD }}` tokens (optional padding around the ref).
# The ref itself can't contain whitespace, which keeps the classes disjoint from `\s*`
# (no overlapping quantifiers -> linear matching, see SonarQube S5852).
_OP_REF_PATTERN: Final = re.compile(r"\{\{\s*(op://[^\s}]+)\s*\}\}")


async def _load_op_item(vault: str, item: str) -> dict[str, str]:
    """
    Fetch an entire 1Password item in a SINGLE `op item get` call and return a
    lookup of "op://vault/item/section/field" -> value for every field.

    Keys are lowercased because 1Password resolves section/field references
    case-insensitively (e.g. the template uses `COMMON` while the item's
    section label is `common`).
    """
    # vault/item come from self-authored op:// template refs and are passed as a fixed
    # argument list (no shell), so this is not command-injection-exploitable.
    stdout, _ = await run_command(["op", "item", "get", item, "--vault", vault, "--format", "json"])  # NOSONAR
    data = json.loads(stdout)

    lookup: dict[str, str] = {}
    for field in data.get("fields", []):
        section = field.get("section") or {}
        section_label = section.get("label") or section.get("id")
        label = field.get("label")
        if not section_label or label is None:
            continue
        # An existing-but-empty field has no "value" key; `op inject` resolves
        # it to an empty string, so we match that (only a truly-missing
        # reference should error during substitution).
        key = f"op://{vault}/{item}/{section_label}/{label}".lower()
        lookup[key] = field.get("value") or ""
    return lookup


async def secret_inject_drop_empty(source_file_path: str, destination_path: str) -> None:
    """
    Resolve `{{op://VAULT/ITEM/SECTION/FIELD}}` references in a rendered flat
    JSON config and write the result to destination_path.

    Replaces per-field `op inject` lookups with one bulk `op item get` per item.
    Keys whose secret is missing or empty in 1Password are dropped entirely so
    the pod never receives empty config values.
    """
    async with aiofiles.open(source_file_path) as f:
        config = json.loads(await f.read())

    lookups: dict[tuple[str, str], dict[str, str]] = {}
    resolved: dict = {}
    dropped: list[str] = []
    for key, value in config.items():
        if isinstance(value, str):
            for match in _OP_REF_PATTERN.finditer(value):
                ref = match.group(1)
                _, _, vault, item, *_ = ref.split("/")  # op://VAULT/ITEM/SECTION/FIELD
                if (vault, item) not in lookups:
                    lookups[(vault, item)] = await _load_op_item(vault, item)
                # `.get()` -> "" for a present-but-empty field, None when absent.
                value = value.replace(match.group(0), lookups[(vault, item)].get(ref.lower()) or "")
        if value == "":
            dropped.append(key)
        else:
            resolved[key] = value

    async with aiofiles.open(destination_path, "w") as f:
        await f.write(json.dumps(resolved, indent=4) + "\n")
    if dropped:
        logger.warning(
            f"Dropped {len(dropped)} empty/missing key(s) from {os.path.basename(destination_path)} "
            f"(not set in 1Password): {', '.join(sorted(set(dropped)))}"
        )
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
                "--reveal",
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

    async def get_all_fields_for_tenant(self: "OnePasswordUtil") -> list[str]:
        """
        Get all fields for a tenant from a 1Password item
        """
        commands = ["op", "--vault", self.vault, "item", "get", self.server_item, "--format", "json"]
        fields_json, _ = await run_command(commands)
        fields_json = json.loads(fields_json)
        fields = []
        for field in fields_json["fields"]:
            if field.get("section") and field.get("section").get("label") == self.tenant:
                fields.append((field["label"], field["id"]))
        return fields

    async def delete_tenant_fields(self: "OnePasswordUtil") -> None:
        """
        Delete all fields for a tenant from a 1Password item
        """
        fields = await self.get_all_fields_for_tenant()
        commands = [
            "op",
            "--vault",
            self.vault,
            "item",
            "edit",
            self.server_item,
            *[f"{field[1]}[delete]=" for field in fields],
        ]
        await run_command(commands)
