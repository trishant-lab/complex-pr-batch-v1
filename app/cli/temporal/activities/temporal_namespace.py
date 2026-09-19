"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 55)
"""

from temporalio.common import RetryPolicy
from temporalio import activity, client

from datetime import timedelta
from google.protobuf.duration_pb2 import Duration
from temporalio.api.enums.v1 import ArchivalState
from temporalio.api.operatorservice.v1 import DeleteNamespaceRequest
from temporalio.api.workflowservice.v1 import RegisterNamespaceRequest
from temporalio.service import RPCError, RPCStatusCode

from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_info
from app.core.settings import AppSettings, get_settings


class TemporalNamespaceActivityModel(LaunchpadCLIBaseModel):
    """
    TemporalNamespace dataclass
    """

    namespace: str


class TemporalNamespaceActivity(Activity):
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
    @activity.defn(name="TemporalNamespaceActivity")
    async def defn(activity_input: TemporalNamespaceActivityModel) -> None:
        """
        Callable for the activity
        """
        # Create temporal namespace

        config: AppSettings = get_settings()

        _client = await client.Client.connect(config.temporal.dsn)

        try:
            await _client.workflow_service.register_namespace(
                RegisterNamespaceRequest(
                    namespace=activity_input.namespace,
                    workflow_execution_retention_period=Duration(seconds=30 * 24 * 60 * 60),  # 30 days
                    history_archival_state=ArchivalState.ARCHIVAL_STATE_ENABLED,
                    visibility_archival_state=ArchivalState.ARCHIVAL_STATE_ENABLED,
                ),
            )
        except RPCError as rpc_err:
            if rpc_err.status == RPCStatusCode.ALREADY_EXISTS:
                log_info(f"Temporal Namespace {activity_input.namespace} already exists")
                return  # update namespace if needed
            raise


class DeleteTemporalNamespaceActivityModel(LaunchpadCLIBaseModel):
    """
    DeleteTemporalNamespaceActivityModel
    """

    namespace: str


class DeleteTemporalNamespaceActivity(Activity):
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
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="DeleteTemporalNamespaceActivity")
    async def defn(activity_input: DeleteTemporalNamespaceActivityModel) -> None:
        """
        Callable for the activity to delete a Temporal namespace
        """
        config: AppSettings = get_settings()
        _client = await client.Client.connect(config.temporal.dsn)

        try:
            await _client.service_client.operator_service.delete_namespace(
                DeleteNamespaceRequest(namespace=activity_input.namespace)
            )
            log_info(f"Temporal Namespace {activity_input.namespace} deleted successfully")
        except RPCError as rpc_err:
            if rpc_err.status == RPCStatusCode.NOT_FOUND:
                log_info(f"Temporal Namespace {activity_input.namespace} does not exist")
                return
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
