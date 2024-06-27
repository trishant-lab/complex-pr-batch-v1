from coverage.annotate import os

from app.cli.jeeves.jeeves import JeevesSpec
from app.core.settings import AppSettings, get_settings
from app.s3_utils import copy_files_to_s3


def add_ai_voices_to_storage(jeeves: JeevesSpec) -> None:
    """
    Add AI voices to storage
    """
    config: AppSettings = get_settings()
    source_folder_path: str = "r2/media/jeeves/ai_voices/"
    dest_folder_path: str = f"r2/media/jeeves/{jeeves.tenant}/voices/"
    copy_files_to_s3(input_path=source_folder_path, output_path=dest_folder_path, config=config)

    os.system(f"mc alias set r2 {config.jeeves.r2_url} {config.jeeves.r2_access_key} {config.jeeves.r2_secret_key}")  # nosec
    os.system(f"mc mirror --remove --overwrite {source_folder_path} {dest_folder_path}")  # nosec
