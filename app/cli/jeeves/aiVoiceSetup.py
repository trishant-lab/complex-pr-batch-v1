import os

from app.cli.jeeves.jeeves import JeevesSpec
from app.cli.temporal.core.log import log_info
from app.core.settings import AppSettings, get_settings


def add_ai_voices_to_storage(jeeves: JeevesSpec) -> None:
    """
    Add AI voices to storage
    """
    config: AppSettings = get_settings()
    source_folder_path: str = f"r2/{config.jeeves.r2_bucket}/jeeves/ai_voices/"
    dest_folder_path: str = f"r2/{config.jeeves.r2_bucket}/jeeves/{jeeves.tenant}/voices/"

    os.system(f"mc alias set r2 {config.jeeves.r2_url} {config.jeeves.r2_access_key} {config.jeeves.r2_secret}")  # nosec
    os.system(f"mc cp -r {source_folder_path} {dest_folder_path}")  # nosec

    log_info("AI voices are added successfully.")
