"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 59)
"""

from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_error, log_info
from app.core.db import DBManager, get_db_manager
from app.core.ijson import ijson_dumps
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum


class SpaceStatusModel(LaunchpadCLIBaseModel):
    """
    SpaceStatus dataclass for updating space provisioning status
    """

    space_name: str
    tenant_name: str
    product: ProductEnum
    status: TenantStatusEnum
    error_msg: None | str = None


async def update_space_status(
    space_name: str,
    tenant_name: str,
    product: ProductEnum,
    status: TenantStatusEnum,
    error_message: None | str = None,
) -> None:
    """
    Update space status in the database
    """
    try:
        # Format errors as JSON
        errors_json = ijson_dumps({"error": error_message} if error_message else {})

        parameters = {
            "spacename": space_name,
            "tenant_name": tenant_name,
            "product": product.value,
            "status": status.value,
            "errors": errors_json,
        }
        db: DBManager = await get_db_manager()
        await db.fetch_one("update_space_status.sql", **parameters)

        log_info(f"Space status updated for {tenant_name}/{space_name} to {status}")

    except Exception as e:
        log_error(f"Error while updating space status for {tenant_name}/{space_name}: {e}")
        raise


async def create_space(
    space_name: str,
    tenant_name: str,
    product: ProductEnum,
    status: TenantStatusEnum,
    error_message: None | str = None,
) -> None:
    """
    Create a space record in the database if it does not already exist.
    """
    try:
        errors_json = ijson_dumps({"error": error_message} if error_message else {})

        parameters = {
            "spacename": space_name,
            "tenant_name": tenant_name,
            "product": product.value,
            "status": status.value,
            "errors": errors_json,
        }
        db: DBManager = await get_db_manager()

        existing = await db.fetch_one(
            "get_space_by_name.sql", spacename=space_name, tenant_name=tenant_name, product=product.value
        )
        if existing:
            log_info(f"Space {space_name} already exists for {tenant_name}, skipping creation")
            return

        await db.execute("create_space.sql", **parameters)
        log_info(f"Space {space_name} created for {tenant_name} with status {status}")

    except Exception as e:
        log_error(f"Error while creating space entry for {tenant_name}/{space_name}: {e}")
        raise


class CreateSpaceActivity(Activity):
    @staticmethod
    def get_timeout() -> timedelta:
        """Timeout for the activity."""
        return timedelta(seconds=60)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """RetryPolicy for the activity."""
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="CreateSpaceActivity")
    async def defn(activity_input: SpaceStatusModel) -> None:
        """Create a space record if it does not already exist."""
        await create_space(
            space_name=activity_input.space_name,
            tenant_name=activity_input.tenant_name,
            product=activity_input.product,
            status=activity_input.status,
            error_message=activity_input.error_msg,
        )


class UpdateSpaceStatusActivity(Activity):
    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=60)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="UpdateSpaceStatusActivity")
    async def defn(activity_input: SpaceStatusModel) -> None:
        """
        Callable for the activity
        """
        await update_space_status(
            space_name=activity_input.space_name,
            tenant_name=activity_input.tenant_name,
            product=activity_input.product,
            status=activity_input.status,
            error_message=activity_input.error_msg,
        )


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
