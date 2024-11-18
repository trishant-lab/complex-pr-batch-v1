from temporalio import activity, workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from datetime import timedelta
    from app.cli.k8s_util import ResourceKindEnum, get_custom_objects_api
    from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
    from app.cli.temporal.core.log import log_info


class TenantCrdCreationActivityModel(LaunchpadCLIBaseModel):
    """
    TenantCrdCreationActivityModel
    """

    kind: ResourceKindEnum
    tenant: str
    data: dict | None = None
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
        k8s_custom_objects_api = get_custom_objects_api()

        body = {
            "apiVersion": "apiextensions.k8s.io/v1",
            "kind": activity_model.kind.value,
            "metadata": {
                "name": f"{activity_model.product}-{activity_model.tenant}",
                "namespace": "default",
            },
            "spec": {
                "tenant": activity_model.tenant,
                "data": activity_model.data,
            },
        }

        k8s_custom_objects_api.create_namespaced_custom_object(
            group="com.softwareartistry",
            version="v1",
            namespace="default",
            plural=f"{activity_model.product.lower()}tenants",
            body=body,
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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5, backoff_coefficient=2)

    @staticmethod
    @activity.defn(name="TenantCrdDeletionActivity")
    async def defn(activity_model: TenantCrdDeletionActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_custom_objects_api = get_custom_objects_api()

        k8s_custom_objects_api.delete_namespaced_custom_object(
            group="com.softwareartistry",
            version="v1",
            namespace="default",
            plural=f"{activity_model.product.lower()}tenants",
            name=f"{activity_model.product}-{activity_model.tenant}",
        )


class GetTenantCrdActivityModel(LaunchpadCLIBaseModel):
    """
    GetTenantCrdActivityModel
    """

    kind: ResourceKindEnum
    tenant: str
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
            name=f"{activity_model.product}-{activity_model.tenant}",
        )
