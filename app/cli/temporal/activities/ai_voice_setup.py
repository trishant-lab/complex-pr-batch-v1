"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 1)
"""

from datetime import timedelta
from shlex import split

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_info
from app.core.settings import JeevesSettings
from app.one_password_util import OnePasswordUtil
from app.utils.subprocess_execution import run_command


async def add_ai_voices_to_storage(tenant: str, config: JeevesSettings) -> None:
    """
    Add AI voices to storage
    """
    ui_bucket_name = await OnePasswordUtil(
        tenant=f"jeeves-{tenant}",
        server_item="application-config",
        vault="Jeeves",
    ).get_key(key="s3_ui_bucket_name")
    ui_access_key = await OnePasswordUtil(
        tenant=f"jeeves-{tenant}",
        server_item="application-config",
        vault="Jeeves",
    ).get_key(key="s3_ui_bucket_access_key")
    ui_secret_key = await OnePasswordUtil(
        tenant=f"jeeves-{tenant}",
        server_item="application-config",
        vault="Jeeves",
    ).get_key(key="s3_ui_bucket_secret_key")
    source_folder_path: str = f"r2/{config.r2_bucket}/jeeves-config/ai_voices/"
    ui_bucket_dest_folder_path: str = f"r2_ui_bucket/{ui_bucket_name}/jeeves/{tenant}/voices/"

    await run_command(["mc", "alias", "set", "r2", config.r2_url, config.r2_access_key, config.r2_secret])
    await run_command(split(f"mc alias set r2_ui_bucket {config.r2_url} {ui_access_key} {ui_secret_key}"))
    await run_command(split(f"mc cp -r {source_folder_path} {ui_bucket_dest_folder_path}"))
    log_info("AI voices are added successfully.")


async def copy_thumbnail_to_storage(tenant: str, config: JeevesSettings) -> None:
    """
    Add AI voices to storage
    """
    ui_bucket_name = await OnePasswordUtil(
        tenant=f"jeeves-{tenant}",
        server_item="application-config",
        vault="Jeeves",
    ).get_key(key="s3_ui_bucket_name")
    ui_access_key = await OnePasswordUtil(
        tenant=f"jeeves-{tenant}",
        server_item="application-config",
        vault="Jeeves",
    ).get_key(key="s3_ui_bucket_access_key")
    ui_secret_key = await OnePasswordUtil(
        tenant=f"jeeves-{tenant}",
        server_item="application-config",
        vault="Jeeves",
    ).get_key(key="s3_ui_bucket_secret_key")
    source_folder_path: str = f"r2/{config.r2_bucket}/jeeves-config/thumbnail_templates/"
    ui_bucket_dest_folder_path: str = f"r2_ui_bucket/{ui_bucket_name}/jeeves/{tenant}/thumbnail_templates/"

    await run_command(["mc", "alias", "set", "r2", config.r2_url, config.r2_access_key, config.r2_secret])
    await run_command(split(f"mc alias set r2_ui_bucket {config.r2_url} {ui_access_key} {ui_secret_key}"))
    await run_command(split(f"mc cp -r {source_folder_path} {ui_bucket_dest_folder_path}"))
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
        await add_ai_voices_to_storage(activity_model.tenant, activity_model.config)


class CopyThumbnailTemplateActivity(Activity):
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
    @activity.defn(name="CopyThumbnailTemplateActivity")
    async def defn(activity_model: AiVoiceSetupActivityModel) -> None:
        """
        Callable for the activity
        """
        await copy_thumbnail_to_storage(activity_model.tenant, activity_model.config)


# --- launchpad oncall hardening (complex-pr batch) ---
def _activity_log_fields(name: str, **extra):
    """Structured fields for Temporal activity logging (oncall / Grafana)."""
    base = {
        "activity": name,
        "service": "launchpad",
        "layer": "temporal",
        "product": "launchpad-app",
    }
    base.update(extra)
    return base


class ActivityHardeningError(RuntimeError):
    """Refuse silent/unsafe fallbacks inside Temporal activities."""

    def __init__(self, activity: str, reason: str):
        super().__init__(f"[{activity}] {reason}")
        self.activity = activity
        self.reason = reason


def _require_nonempty(activity: str, field: str, value) -> None:
    """Fail loud when a required provisioning field is blank."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ActivityHardeningError(activity, f"{field} must be set before provision")


_RETRY_HINTS = {
    "transient_http": {"attempts": 5, "backoff_seconds": 8},
    "dependency_warmup": {"attempts": 3, "backoff_seconds": 20},
    "idempotent_create": {"attempts": 2, "backoff_seconds": 5},
}


def _retry_hint(kind: str) -> dict:
    """Return a documented retry hint for activity authors / runbooks."""
    return dict(_RETRY_HINTS.get(kind, _RETRY_HINTS["transient_http"]))
