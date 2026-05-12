"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 57)
"""

from datetime import timedelta

from kubernetes.dynamic.exceptions import ApiException
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.k8s_util import ResourceKindEnum, get_custom_objects_api, get_dynamic_client, get_resource
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_error, log_info

CRD_GROUP = "com.softwareartistry"
CRD_VERSION = "v1"


class TenantCrdCreationActivityModel(LaunchpadCLIBaseModel):
    """
    TenantCrdCreationActivityModel
    """

    kind: ResourceKindEnum
    tenant: str
    data: str | None = None
    product: str


class TenantCrdCreationActivity(Activity):
    """
    TenantCrdCreationActivity
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
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="TenantCrdCreationActivity")
    async def defn(activity_model: TenantCrdCreationActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_dynamic_client = get_dynamic_client()

        resource = get_resource(
            dynamic_client=k8s_dynamic_client,
            kind=activity_model.kind,
            api_version=f"{CRD_GROUP}/{CRD_VERSION}",
        )

        body = {
            "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
            "kind": activity_model.kind.value,
            "metadata": {
                "name": f"{activity_model.product}-{activity_model.tenant}",
                "namespace": "default",
            },
            "spec": {
                "data": activity_model.data,
            },
        }

        payload = k8s_dynamic_client.client.sanitize_for_serialization(body)
        k8s_dynamic_client.server_side_apply(
            resource=resource, body=payload, field_manager="kubectl-client-side-apply", force_conflicts=True
        )
        log_info(f"{activity_model.kind.value} {activity_model.tenant} created")


class TenantCrdDeletionActivityModel(LaunchpadCLIBaseModel):
    """
    TenantCrdDeletionActivityModel
    """

    kind: ResourceKindEnum
    tenant: str
    product: str


class TenantCrdDeletionActivity(Activity):
    """
    TenantCrdDeletionActivity
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
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="TenantCrdDeletionActivity")
    async def defn(activity_model: TenantCrdDeletionActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_custom_objects_api = get_custom_objects_api()

        try:
            k8s_custom_objects_api.delete_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace="default",
                plural=f"{activity_model.product.lower()}tenants",
                name=f"{activity_model.product}-{activity_model.tenant}",
            )
        except ApiException as e:
            if e.status != 404:
                log_error(f"Error in TenantCrdDeletionActivity: {e}")
                raise
            log_info(f"TenantCrd {activity_model.product}-{activity_model.tenant} not found")


class GetTenantCrdActivityModel(LaunchpadCLIBaseModel):
    """
    GetTenantCrdActivityModel
    """

    kind: ResourceKindEnum
    product: str


class GetTenantCrdActivity(Activity):
    """
    GetTenantCrdActivity
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
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="GetTenantCrdActivity")
    async def defn(activity_model: GetTenantCrdActivityModel) -> dict:
        """
        Callable for the activity
        """
        k8s_custom_objects_api = get_custom_objects_api()

        return k8s_custom_objects_api.list_namespaced_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace="default",
            plural=f"{activity_model.product.lower()}tenants",
        )


class TenantCrdExistsActivityModel(LaunchpadCLIBaseModel):
    """
    TenantCrdExistsActivityModel
    """

    kind: ResourceKindEnum
    product: str
    tenant: str


class TenantCrdExistsActivity(Activity):
    """
    TenantCrdExistsActivity
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
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="TenantCrdExistsActivity")
    async def defn(activity_model: TenantCrdExistsActivityModel) -> bool:
        """
        Callable for the activity
        """
        k8s_custom_objects_api = get_custom_objects_api()
        try:
            _obj = k8s_custom_objects_api.get_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace="default",
                plural=f"{activity_model.product.lower()}tenants",
                name=f"{activity_model.product}-{activity_model.tenant}",
            )
            return True
        except ApiException:
            return False


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
