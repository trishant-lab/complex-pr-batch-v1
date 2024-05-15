from cryptography.fernet import Fernet

from app.cli.veritable.common import VeritableSpec, OnepasswordVaultName
from app.core.settings import AppSettings, get_settings
from app.onepasswordutil import OnePasswordUtil


def generate_fernet_key_and_store_in_1password(veritable: VeritableSpec) -> None:
    """
    Generate and store in 1Password fernet key
    """
    config: AppSettings = get_settings()

    fernet_value = Fernet.generate_key().decode()

    OnePasswordUtil(
        tenant=veritable.tenant,
        server_item=f"veritable-tenant-config-{config.env}",
        vault=OnepasswordVaultName
    ).insert_if_not_exists("fernet_key", fernet_value)
