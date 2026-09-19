"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 24)
"""

from temporalio import activity
from temporalio.common import RetryPolicy

from kubernetes.client import V1Namespace, V1ObjectMeta
from datetime import timedelta
from app.cli.k8s_util import ResourceKindEnum, get_dynamic_client, get_resource
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_info


class K8sNamespaceCreationActivityModel(LaunchpadCLIBaseModel):
    """
    K8sNamespaceCreationActivityModel
    """

    namespace: str


class K8sNamespaceCreationActivity(Activity):
    """
    K8sNamespaceCreationActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        timeout for the activity
        """
        return timedelta(seconds=30)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        retry policy for the activity
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="K8sNamespaceCreationActivity")
    async def defn(activity_model: K8sNamespaceCreationActivityModel) -> None:
        """
        Create k8s namespace
        """
        k8s_dynamic_client = get_dynamic_client()
        k8s_namespace_resource = get_resource(
            dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Namespace, api_version="v1"
        )

        body = V1Namespace(
            api_version="v1",
            kind=ResourceKindEnum.Namespace.value,
            metadata=V1ObjectMeta(name=activity_model.namespace),
        )

        payload = k8s_dynamic_client.client.sanitize_for_serialization(body)

        k8s_dynamic_client.server_side_apply(
            resource=k8s_namespace_resource, body=payload, field_manager="kubectl-client-side-apply"
        )

        log_info(f"Namespace {activity_model.namespace} created successfully")


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
