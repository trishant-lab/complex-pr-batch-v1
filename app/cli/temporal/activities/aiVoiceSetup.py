from temporalio.common import RetryPolicy
from temporalio import activity

import os
from datetime import timedelta
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_info
from app.core.settings import JeevesSettings
from app.onepasswordutil import OnePasswordUtil


def add_ai_voices_to_storage(tenant: str, config: JeevesSettings) -> None:
    """
    Add AI voices to storage
    """
    ui_bucket_name = OnePasswordUtil(
        tenant=f"jeeves_{tenant}",
        server_item="application-config",
        vault="Jeeves",
    ).get_key(key="s3_ui_bucket_name")
    ui_access_key = OnePasswordUtil(
        tenant=f"jeeves_{tenant}",
        server_item="application-config",
        vault="Jeeves",
    ).get_key(key="s3_ui_bucket_access_key")
    ui_secret_key = OnePasswordUtil(
        tenant=f"jeeves_{tenant}",
        server_item="application-config",
        vault="Jeeves",
    ).get_key(key="s3_ui_bucket_secret_key")
    source_folder_path: str = f"r2/{config.r2_bucket}/jeeves/ai_voices/"
    dest_folder_path: str = f"r2/{config.r2_bucket}/jeeves/{tenant}/voices/"
    ui_bucket_dest_folder_path: str = f"r2_ui_bucket/{ui_bucket_name}/jeeves/{tenant}/voices/"

    os.system(f"mc alias set r2 {config.r2_url} {config.r2_access_key} {config.r2_secret}")  # nosec
    os.system(f"mc cp -r {source_folder_path} {dest_folder_path}")  # nosec
    os.system(f"mc alias set r2_ui_bucket {config.r2_url} {ui_access_key} {ui_secret_key}")  # nosec
    os.system(f"mc cp -r {source_folder_path} {ui_bucket_dest_folder_path}")  # nosec
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
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="AiVoiceSetupActivity")
    async def defn(activity_model: AiVoiceSetupActivityModel) -> None:
        """
        Callable for the activity
        """
        add_ai_voices_to_storage(activity_model.tenant, activity_model.config)
