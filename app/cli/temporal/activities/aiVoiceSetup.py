from datetime import timedelta
import os

from temporalio.common import RetryPolicy
from temporalio.activity import activity

from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
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


class AiVoiceSetupActivityModel(LaunchpadCLIBaseModel):
    """
    AiVoiceSetupActivityModel
    """

    tenant: str
    config: JeevesSettings


class AiVoiceSetupActivity(Activity):
    """
    AiVoiceSetupActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(initial_interval=timedelta(seconds=1), backoff_coefficient=2, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="AiVoiceSetupActivity")
    async def defn(activity_model: AiVoiceSetupActivityModel) -> None:
        """
        Callable for the activity
        """
        add_ai_voices_to_storage(activity_model.tenant, activity_model.config)
