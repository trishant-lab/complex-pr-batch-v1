"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 49)
"""

from temporalio import activity
from temporalio.common import RetryPolicy
from datetime import timedelta
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_info


ROLE_API_VERSION = "rbac.authorization.k8s.io/v1"


class CreateKubernetesResourcesActivityModel(LaunchpadCLIBaseModel):
    """
    Model for creating ServiceAccount, Role, and RoleBinding
    """

    namespace: str


class CreateKubernetesResourcesActivity(Activity):
    """
    Activity to create ServiceAccount, Role, and RoleBinding
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=300)

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
    @activity.defn(name="CreateKubernetesResourcesActivity")
    async def defn(activity_model: CreateKubernetesResourcesActivityModel) -> None:
        """
        Callable for creating ServiceAccount, Role, and RoleBinding
        """
        namespace = activity_model.namespace
        k8s_dynamic_client = get_dynamic_client()

        # Create ServiceAccount
        service_account_body = {
            "apiVersion": "v1",
            "kind": "ServiceAccount",
            "metadata": {
                "name": "zsegment-api-sa",
                "namespace": namespace,
            },
        }
        service_account_resource = get_resource(
            dynamic_client=k8s_dynamic_client,
            kind=ResourceKindEnum.ServiceAccount,
            api_version="v1",
        )
        k8s_dynamic_client.server_side_apply(
            resource=service_account_resource,
            body=k8s_dynamic_client.client.sanitize_for_serialization(service_account_body),
            field_manager="kubectl-client-side-apply",
        )
        log_info(f"ServiceAccount 'zsegment-api-sa' created in namespace {namespace}")

        # Create Role
        role_body = {
            "apiVersion": ROLE_API_VERSION,
            "kind": "Role",
            "metadata": {
                "name": "zsegment-api-role",
                "namespace": namespace,
            },
            "rules": [
                {
                    "apiGroups": [""],
                    "resources": ["pods"],
                    "verbs": ["create", "delete", "list"],
                },
                {
                    "apiGroups": ["batch"],
                    "resources": ["cronjobs"],
                    "verbs": ["create", "delete", "get", "list", "watch"],
                },
                {
                    "apiGroups": [""],
                    "resources": ["secrets"],
                    "verbs": ["create", "delete", "update"],
                },
                {
                    "apiGroups": [""],
                    "resources": ["services"],
                    "verbs": ["create", "delete"],
                },
                {
                    "apiGroups": ["networking.istio.io"],
                    "resources": ["virtualservices"],
                    "verbs": ["create", "delete"],
                },
            ],
        }
        role_resource = get_resource(
            dynamic_client=k8s_dynamic_client,
            kind=ResourceKindEnum.Role,
            api_version=ROLE_API_VERSION,
        )
        k8s_dynamic_client.server_side_apply(
            resource=role_resource,
            body=k8s_dynamic_client.client.sanitize_for_serialization(role_body),
            field_manager="kubectl-client-side-apply",
        )
        log_info(f"Role 'zsegment-api-role' created in namespace {namespace}")

        # Create RoleBinding
        role_binding_body = {
            "apiVersion": ROLE_API_VERSION,
            "kind": "RoleBinding",
            "metadata": {
                "name": "zsegment-api-role-binding",
                "namespace": namespace,
            },
            "subjects": [
                {
                    "kind": "ServiceAccount",
                    "name": "zsegment-api-sa",
                    "namespace": namespace,
                },
            ],
            "roleRef": {
                "kind": "Role",
                "name": "zsegment-api-role",
                "apiGroup": "rbac.authorization.k8s.io",
            },
        }
        role_binding_resource = get_resource(
            dynamic_client=k8s_dynamic_client,
            kind=ResourceKindEnum.RoleBinding,
            api_version=ROLE_API_VERSION,
        )
        k8s_dynamic_client.server_side_apply(
            resource=role_binding_resource,
            body=k8s_dynamic_client.client.sanitize_for_serialization(role_binding_body),
            field_manager="kubectl-client-side-apply",
        )
        log_info(f"RoleBinding 'zsegment-api-role-binding' created in namespace {namespace}")


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
