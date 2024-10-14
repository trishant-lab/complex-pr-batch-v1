import os

from app.cli.temporal.core.log import log_info
from app.core.settings import JeevesSettings


def add_ai_voices_to_storage(tenant: str, config: JeevesSettings) -> None:
    """
    Add AI voices to storage
    """
    source_folder_path: str = f"r2/{config.r2_bucket}/jeeves/ai_voices/"
    dest_folder_path: str = f"r2/{config.r2_bucket}/jeeves/{tenant}/voices/"

    os.system(f"mc alias set r2 {config.r2_url} {config.r2_access_key} {config.r2_secret}")  # nosec
    os.system(f"mc cp -r {source_folder_path} {dest_folder_path}")  # nosec

    log_info("AI voices are added successfully.")
