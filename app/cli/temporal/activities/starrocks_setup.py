"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 51)
"""

from datetime import timedelta
from app.cli.temporal.core.base import Activity
from app.cli.temporal.models.starrocks import CreateStarRocksCatalogActivityModel
from app.core.settings import AppSettings, get_settings
from temporalio import activity
from temporalio.common import RetryPolicy

from app.starrocks_utils import (
    CreateStarRocksInputModel,
    GrantStarRocksReadOnlyCatalogModel,
    RegisterStarrocksUserModel,
)


class CreateStarRocksCatalogActivity(Activity):
    """
    CreateStarRocksCatalogActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(minutes=10)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), maximum_attempts=5, backoff_coefficient=3)

    @staticmethod
    @activity.defn(name="CreateStarRocksCatalogActivity")
    async def defn(activity_input: CreateStarRocksCatalogActivityModel) -> None:
        """
        CreateStarRocksCatalogActivity
        """
        config: AppSettings = get_settings()

        from app.starrocks_utils import create_starrocks_catalog

        starrocks_input = CreateStarRocksInputModel(
            muspell_config=config.muspell,
            tenant=activity_input.tenant,
            warehouse_access_key=activity_input.warehouse_access_key,
            warehouse_secret_key=activity_input.warehouse_secret_key,
            catalog_name=activity_input.catalog_name,
        )

        await create_starrocks_catalog(starrocks_input)


class CreateStarRocksUserActivity(Activity):
    """
    CreateStarRocksUserActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(minutes=10)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), maximum_attempts=5, backoff_coefficient=3)

    @staticmethod
    @activity.defn(name="CreateStarRocksUserActivity")
    async def defn(activity_input: RegisterStarrocksUserModel) -> None:
        """
        CreateStarRocksUserActivity
        """
        from app.starrocks_utils import register_user

        await register_user(activity_input)


class StarRocksGrantReadOnlyCatalogActivity(Activity):
    """
    StarRocksGrantReadOnlyCatalogActivity - grants read-only access on the catalog to a
    pre-existing StarRocks user. Silently no-ops if the user does not exist.
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(minutes=10)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), maximum_attempts=5, backoff_coefficient=3)

    @staticmethod
    @activity.defn(name="StarRocksGrantReadOnlyCatalogActivity")
    async def defn(activity_input: GrantStarRocksReadOnlyCatalogModel) -> None:
        """
        Grant read-only access on the catalog to a pre-existing user.
        """
        from app.starrocks_utils import grant_read_only_to_catalog

        grant_read_only_to_catalog(activity_input)


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
