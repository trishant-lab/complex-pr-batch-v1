from temporalio import activity, workflow
from temporalio.common import RetryPolicy


with workflow.unsafe.imports_passed_through():
    from datetime import timedelta
    from kubernetes.client import V1Service, V1ObjectMeta, V1ServiceSpec, V1ServicePort
    from app.cli.k8s_util import ResourceKindEnum, get_dynamic_client, get_resource
    from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
    from app.cli.temporal.core.log import log_info


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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)

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
        k8s_dynamic_client.server_side_apply(resource=resource, body=payload, field_manager="kubectl-client-side-apply")
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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)

    @staticmethod
    @activity.defn(name="DeleteKubernetesServiceActivity")
    async def defn(activity_model: DeleteKubernetesServiceActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_dynamic_client = get_dynamic_client()
        resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Service, api_version="v1")
        k8s_dynamic_client.client.delete(
            resource=resource, name=activity_model.service_name, namespace=activity_model.namespace
        )
        log_info(f"Service {activity_model.service_name} deleted in namespace {activity_model.namespace}")
