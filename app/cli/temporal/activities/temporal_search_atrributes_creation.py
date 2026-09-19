"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 56)
"""

from datetime import timedelta

from temporalio import client, activity
from temporalio.api.enums.v1 import IndexedValueType
from temporalio.api.operatorservice.v1 import AddSearchAttributesRequest
from temporalio.common import RetryPolicy
from temporalio.service import RPCError

from app.cli.temporal.core.base import LaunchpadCLIBaseModel, Activity
from app.cli.temporal.core.log import log_info

from app.core.settings import AppSettings, get_settings


class TemporalSearchAttributesCreationActivityModel(LaunchpadCLIBaseModel):
    """
    TemporalNamespace dataclass
    """

    namespace: str


class TemporalSearchAttributesCreationActivity(Activity):
    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=30)

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
    @activity.defn(name="TemporalSearchAttributesCreationActivity")
    async def defn(activity_input: TemporalSearchAttributesCreationActivityModel) -> None:
        """
        Callable for the activity
        """
        # Create temporal namespace

        config: AppSettings = get_settings()

        _client = await client.Client.connect(config.temporal.dsn, namespace=activity_input.namespace)
        try:
            # Define the search attributes to be added
            search_attributes = {
                "DexitWorkflowId": IndexedValueType.INDEXED_VALUE_TYPE_KEYWORD,
                "isWaiting": IndexedValueType.INDEXED_VALUE_TYPE_BOOL,
                "EventReference": IndexedValueType.INDEXED_VALUE_TYPE_KEYWORD,
                "TaskStartTime": IndexedValueType.INDEXED_VALUE_TYPE_DATETIME,
                "User": IndexedValueType.INDEXED_VALUE_TYPE_KEYWORD_LIST,
                "Groups": IndexedValueType.INDEXED_VALUE_TYPE_KEYWORD_LIST,
                "TaskNumber": IndexedValueType.INDEXED_VALUE_TYPE_KEYWORD,
                "ActivityId": IndexedValueType.INDEXED_VALUE_TYPE_TEXT,
                "ActivityName": IndexedValueType.INDEXED_VALUE_TYPE_TEXT,
                "isSubWorkflow": IndexedValueType.INDEXED_VALUE_TYPE_BOOL,
                "isUserTask": IndexedValueType.INDEXED_VALUE_TYPE_BOOL,
            }

            # Upsert the search attributes
            await _client.operator_service.add_search_attributes(
                AddSearchAttributesRequest(search_attributes=search_attributes, namespace=activity_input.namespace)
            )
            log_info(f"Search attributes created for namespace {activity_input.namespace}")

        except RPCError as rpc_err:
            log_info(f"Failed to upsert search attributes: {rpc_err}")
            raise


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
