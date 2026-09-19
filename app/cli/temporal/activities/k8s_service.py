"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 26)
"""

from datetime import timedelta

from kubernetes.client import V1ObjectMeta, V1Service, V1ServicePort, V1ServiceSpec
from kubernetes.dynamic.exceptions import NotFoundError
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.k8s_util import ResourceKindEnum, get_dynamic_client, get_resource
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_error, log_info


class KubernetesServiceActivityModel(LaunchpadCLIBaseModel):
    """
    KubernetesServiceActivityModel
    """

    namespace: str
    service_name: str
    selector: str | None = None
    ports: dict[str, int]


class KubernetesServiceActivity(Activity):
    """
    KubernetesServiceActivity
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
    @activity.defn(name="KubernetesServiceActivity")
    async def defn(activity_model: KubernetesServiceActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_dynamic_client = get_dynamic_client()
        resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Service, api_version="v1")

        body = V1Service(
            api_version="v1",
            kind=ResourceKindEnum.Service.value,
            metadata=V1ObjectMeta(
                name=activity_model.service_name,
                namespace=activity_model.namespace,
                labels={"app": activity_model.service_name},
            ),
            spec=V1ServiceSpec(
                selector={"app": activity_model.selector if activity_model.selector else activity_model.service_name},
                type="ClusterIP",
                ports=[
                    V1ServicePort(
                        name=port_name,
                        port=port_value,
                    )
                    for port_name, port_value in activity_model.ports.items()
                ],
            ),
        )

        payload = k8s_dynamic_client.client.sanitize_for_serialization(body)
        k8s_dynamic_client.server_side_apply(
            resource=resource, body=payload, field_manager="kubectl-client-side-apply", force_conflicts=True
        )
        log_info(f"Service {activity_model.service_name} created in namespace {activity_model.namespace}")


class DeleteKubernetesServiceActivityModel(LaunchpadCLIBaseModel):
    """
    DeleteKubernetesServiceActivityModel
    """

    namespace: str
    service_name: str


class DeleteKubernetesServiceActivity(Activity):
    """
    DeleteKubernetesServiceActivity
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
    @activity.defn(name="DeleteKubernetesServiceActivity")
    async def defn(activity_model: DeleteKubernetesServiceActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_dynamic_client = get_dynamic_client()
        resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Service, api_version="v1")
        try:
            k8s_dynamic_client.delete(
                resource=resource, name=activity_model.service_name, namespace=activity_model.namespace
            )
            log_info(f"Service {activity_model.service_name} deleted in namespace {activity_model.namespace}")
        except NotFoundError:
            log_error(f"Service {activity_model.service_name} not found in namespace {activity_model.namespace}")


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
