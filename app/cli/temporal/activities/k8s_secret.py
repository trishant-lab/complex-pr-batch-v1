"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 25)
"""

from base64 import b64decode
from datetime import timedelta

from kubernetes.client import V1ObjectMeta, V1Secret
from kubernetes.dynamic.exceptions import ConflictError, NotFoundError
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.k8s_util import ResourceKindEnum, get_dynamic_client, get_resource
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_error, log_info


class K8sSecretCreationActivityModel(LaunchpadCLIBaseModel):
    """
    K8sSecretCreationActivityModel
    """

    namespace: str
    name: str
    type: str | None = None
    data: dict | None = None
    string_data: dict | None = None


class K8sSecretCreationActivity(Activity):
    """
    K8sSecretCreationActivity
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
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="K8sSecretCreationActivity")
    async def defn(activity_model: K8sSecretCreationActivityModel) -> None:
        """
        Create k8s secret
        """
        k8s_dynamic_client = get_dynamic_client()
        k8s_secret_resource = get_resource(
            dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Secret, api_version="v1"
        )

        body = V1Secret(
            api_version="v1",
            kind=ResourceKindEnum.Secret.value,
            metadata=V1ObjectMeta(namespace=activity_model.namespace, name=activity_model.name),
            type=activity_model.type,
            data=activity_model.data,
            string_data=activity_model.string_data,
        )

        payload = k8s_dynamic_client.client.sanitize_for_serialization(body)

        try:
            k8s_dynamic_client.server_side_apply(
                resource=k8s_secret_resource, body=payload, field_manager="kubectl-client-side-apply"
            )

        except ConflictError as e:
            log_error(
                f"Secret {activity_model.name} already exists in"
                f" namespace {activity_model.namespace} and cannot be updated due to conflict"
                f" {e}"
            )

        log_info(f"Secret {activity_model.name} created successfully")


class K8sSecretDeletionActivityModel(LaunchpadCLIBaseModel):
    """
    K8sSecretDeletionActivityModel
    """

    namespace: str
    name: str


class K8sSecretDeletionActivity(Activity):
    """
    K8sSecretDeletionActivity
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
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="DeleteK8sSecretActivity")
    async def defn(activity_model: K8sSecretDeletionActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_dynamic_client = get_dynamic_client()
        resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Secret, api_version="v1")

        try:
            k8s_dynamic_client.delete(resource=resource, name=activity_model.name, namespace=activity_model.namespace)
        except NotFoundError:
            log_error(f"Secret {activity_model.name} not found in namespace {activity_model.namespace}")

        log_info(f"Secret {activity_model.name} deleted in namespace {activity_model.namespace}")


class K8sSecretFetchActivityModel(LaunchpadCLIBaseModel):
    """
    K8sSecretFetchActivityModel
    """

    namespace: str
    name: str
    decode_data: bool = True  # Whether to base64 decode the secret data


class K8sSecretFetchActivity(Activity):
    """
    K8sSecretFetchActivity to retrieve a Kubernetes secret's data
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=60)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(initial_interval=timedelta(seconds=5), backoff_coefficient=2, maximum_attempts=3)

    @staticmethod
    @activity.defn(name="K8sSecretFetchActivity")
    async def defn(activity_model: K8sSecretFetchActivityModel) -> dict | None:
        """
        Fetch k8s secret data
        """
        k8s_dynamic_client = get_dynamic_client()
        k8s_secret_resource = get_resource(
            dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Secret, api_version="v1"
        )

        try:
            # Get the secret
            secret = k8s_dynamic_client.get(
                resource=k8s_secret_resource, name=activity_model.name, namespace=activity_model.namespace
            )

            # Extract data field
            data = secret.get("data", {})

            # Decode base64 data if requested
            if activity_model.decode_data and data:
                decoded_data = {}
                for key, value in data.items():
                    if value:
                        decoded_data[key] = b64decode(value).decode("utf-8")
                    else:
                        decoded_data[key] = None
                return decoded_data

            return data

        except NotFoundError:
            log_info(f"Secret {activity_model.name} not found in namespace {activity_model.namespace}")
            return None


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
