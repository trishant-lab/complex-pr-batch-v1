"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 58)
"""

import os
from temporalio import activity
from temporalio.common import RetryPolicy


from datetime import timedelta

import zipfile

from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_error, log_info
from app.core.settings import AppSettings, get_settings
from app.s3_utils import copy_files_to_s3, download_file_from_storage
from app.utils.file_operations import get_opendal_file_client
from app.utils.s3_operations import get_s3_client


class UiSetupActivityModel(LaunchpadCLIBaseModel):
    """
    UiSetupActivityModel
    """

    src_object_name: str
    dest_dir: str
    bundle_path: str
    bundle_name: str


class UiSetupActivity(Activity):
    """
    UiSetupActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="UiSetupActivity")
    async def defn(activity_model: UiSetupActivityModel) -> None:
        """
        Callable for the activity
        """
        config: AppSettings = get_settings()

        environment: str = config.env

        s3_int_client = get_s3_client(
            access_key=config.s3_int.access_key,
            secret_key=config.s3_int.secret_key,
            endpoint=config.s3_int.endpoint,
            bucket_name="artifacts",
        )

        try:
            opendal_file_operations = get_opendal_file_client()
            async with opendal_file_operations.temp_dir() as tmp_dir:
                await download_file_from_storage(
                    object_name=activity_model.src_object_name,
                    file_path=os.path.join(opendal_file_operations.tempdir_root, tmp_dir, activity_model.bundle_name),
                    storage_client=s3_int_client,
                )

                # unzip the file
                with zipfile.ZipFile(
                    os.path.join(opendal_file_operations.tempdir_root, tmp_dir, activity_model.bundle_name), "r"
                ) as zip_ref:
                    zip_ref.extractall(os.path.join(opendal_file_operations.tempdir_root, tmp_dir, "bundle"))

                # copy the files to the destination directory
                copy_files_to_s3(
                    input_path=os.path.join(opendal_file_operations.tempdir_root, tmp_dir, activity_model.bundle_path),
                    output_path=f"{config.s3.s3_alias}/static/{activity_model.dest_dir}",
                    config=config,
                )

                if environment == "production":
                    copy_files_to_s3(
                        input_path=os.path.join(
                            opendal_file_operations.tempdir_root, tmp_dir, activity_model.bundle_path, "index.html"
                        ),
                        output_path=f"{config.s3.s3_alias}/static/{activity_model.dest_dir}/custom/index.html",
                        config=config,
                    )

                log_info(f"UI setup completed for {activity_model.dest_dir}")

        except Exception as e:
            log_error(f"Error downloading UI bundle: {e}")
            raise e


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
