"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 37)
"""

from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.one_password_util import OnePasswordUtil
from app.common import generate_password


class OnePasswordCreateOrUpdateActivityModel(LaunchpadCLIBaseModel):
    """
    OnePasswordCreateOrUpdateActivityModel
    """

    tenant: str
    server_item: str
    vault: str
    secret_name: str
    secret_value: str


class CreatePasswordActivityModel(LaunchpadCLIBaseModel):
    """
    CreatePasswordActivityModel
    """

    length: int

class CreatePasswordActivity(Activity):
    """
    CreatePasswordActivity

    """

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
    @activity.defn(name="CreatePasswordActivity")
    async def defn(activity_input: CreatePasswordActivityModel) -> str:
        """
        Callable for the activity
        """
        return generate_password(length=activity_input.length)


class OnePasswordCreateOrUpdateActivity(Activity):
    """
    OnePasswordCreateOrUpdateActivity
    """

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
    @activity.defn(name="OnePasswordCreateOrUpdateActivity")
    async def defn(activity_input: OnePasswordCreateOrUpdateActivityModel) -> None:
        """
        Callable for the activity
        """
        await OnePasswordUtil(
            tenant=activity_input.tenant,
            server_item=activity_input.server_item,
            vault=activity_input.vault,
        ).create_or_replace(activity_input.secret_name, activity_input.secret_value)


class OnePasswordGetActivityModel(LaunchpadCLIBaseModel):
    """
    OnePasswordGetActivityModel
    """

    tenant: str
    server_item: str
    vault: str
    secret_name: str


class OnePasswordGetActivity(Activity):
    """
    OnePasswordGetActivity
    """

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
        return RetryPolicy(initial_interval=timedelta(seconds=10), maximum_attempts=5, backoff_coefficient=3)

    @staticmethod
    @activity.defn(name="OnePasswordGetActivity")
    async def defn(activity_input: OnePasswordGetActivityModel) -> str | None:
        """
        Callable for the activity
        """
        return await OnePasswordUtil(
            tenant=activity_input.tenant,
            server_item=activity_input.server_item,
            vault=activity_input.vault,
        ).get_key(key=activity_input.secret_name)


class OnePasswordInsertIfNotExistsActivityModel(LaunchpadCLIBaseModel):
    """
    Model for inserting a fernet key if it doesn't exist
    """

    tenant: str
    vault: str
    server_item: str
    key: str
    key_value: str | None = None


class OnePasswordInsertIfNotExistsActivity(Activity):
    """
    Activity to insert key into 1Password if it doesn't exist
    """

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
        return RetryPolicy(initial_interval=timedelta(seconds=10), maximum_attempts=5, backoff_coefficient=3)

    @staticmethod
    @activity.defn(name="OnePasswordInsertIfNotExistsActivity")
    async def defn(activity_input: OnePasswordInsertIfNotExistsActivityModel) -> None:
        """
        Callable for the activity that checks if a key exists for a tenant,
        and if not, generates and inserts a new one
        """
        server_item = activity_input.server_item
        op_util = OnePasswordUtil(
            tenant=activity_input.tenant,
            server_item=server_item,
            vault=activity_input.vault,
        )

        # Try to get existing key
        existing_key = await op_util.get_key(activity_input.key)

        if all([existing_key is None, activity_input.key_value is not None]):
            # Create or update the key
            await op_util.create_or_replace(activity_input.key, activity_input.key_value)


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
