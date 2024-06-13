from app.cli.jeeves.jeeves import JeevesSpec
from app.core.settings import AppSettings, get_settings
from app.s3_utils import copy_files_to_s3


def add_ai_voices_to_storage(jeeves: JeevesSpec) -> None:
    """
    Add AI voices to storage
    """
    config: AppSettings = get_settings()
    source_folder_path: str = f"{config.s3.rclone_remote}:media/jeeves/ai_voices/"
    dest_folder_path: str = f"{config.s3.rclone_remote}:media/jeeves/{jeeves.tenant}/voices/"
    copy_files_to_s3(input_path=source_folder_path, output_path=dest_folder_path, config=config)
