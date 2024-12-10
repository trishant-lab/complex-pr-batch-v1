from temporalio import activity, workflow
from temporalio.common import RetryPolicy

from app.cli.k8s_util import get_resource
from app.cli.temporal.core.log import log_error
from kubernetes.dynamic.exceptions import NotFoundError

with workflow.unsafe.imports_passed_through():
    from datetime import timedelta
    from app.cli.k8s_util import get_custom_objects_api, get_dynamic_client
    from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
    from app.cli.temporal.core.log import log_info
    from app.cli.k8s_util import ResourceKindEnum


class TenantCrdCreationActivityModel(LaunchpadCLIBaseModel):
    """
    TenantCrdCreationActivityModel
    """

    kind: str
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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5, backoff_coefficient=2)

    @staticmethod
    @activity.defn(name="TenantCrdCreationActivity")
    async def defn(activity_model: TenantCrdCreationActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_dynamic_client = get_dynamic_client()

        resource = get_resource(
            dynamic_client=k8s_dynamic_client,
            kind=ResourceKindEnum.PractiflyTenant,
            api_version="com.softwareartistry/v1",
        )

        body = {
            "apiVersion": "com.softwareartistry/v1",
            "kind": activity_model.kind,
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
        log_info(f"{activity_model.kind} {activity_model.tenant} created")


class TenantCrdDeletionActivityModel(LaunchpadCLIBaseModel):
    """
    TenantCrdDeletionActivityModel
    """

    kind: str
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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5, backoff_coefficient=2)

    @staticmethod
    @activity.defn(name="TenantCrdDeletionActivity")
    async def defn(activity_model: TenantCrdDeletionActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_custom_objects_api = get_custom_objects_api()

        try:
            k8s_custom_objects_api.delete_namespaced_custom_object(
                group="com.softwareartistry",
                version="v1",
                namespace="default",
                plural=f"{activity_model.product.lower()}tenants",
                name=f"{activity_model.product}-{activity_model.tenant}",
            )
        except NotFoundError:
            log_error(f"TenantCrd {activity_model.product}-{activity_model.tenant} not found")


class GetTenantCrdActivityModel(LaunchpadCLIBaseModel):
    """
    GetTenantCrdActivityModel
    """

    kind: str
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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5, backoff_coefficient=2)

    @staticmethod
    @activity.defn(name="GetTenantCrdActivity")
    async def defn(activity_model: GetTenantCrdActivityModel) -> dict:
        """
        Callable for the activity
        """
        k8s_custom_objects_api = get_custom_objects_api()

        return k8s_custom_objects_api.list_namespaced_custom_object(
            group="com.softwareartistry",
            version="v1",
            namespace="default",
            plural=f"{activity_model.product.lower()}tenants",
        )
