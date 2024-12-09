from temporalio import activity, workflow
from temporalio.common import RetryPolicy


with workflow.unsafe.imports_passed_through():
    from datetime import timedelta
    from app.cli.k8s_util import ResourceKindEnum, get_dynamic_client, get_resource
    from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
    from app.cli.temporal.core.log import log_info


class KubernetesIstioVirtualServiceActivityModel(LaunchpadCLIBaseModel):
    """
    KubernetesIstioVirtualServiceActivityModel
    """

    payload: list
    namespace: str
    host: str
    service_name: str


class KubernetesIstioVirtualServiceActivity(Activity):
    """
    KubernetesIstioVirtualServiceActivity
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
    @activity.defn(name="KubernetesIstioVirtualServiceActivity")
    async def defn(activity_model: KubernetesIstioVirtualServiceActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_dynamic_client = get_dynamic_client()
        resource = get_resource(
            dynamic_client=k8s_dynamic_client,
            kind=ResourceKindEnum.VirtualService,
            api_version="networking.istio.io/v1beta1",
        )

        body = {
            "apiVersion": "networking.istio.io/v1beta1",
            "kind": "VirtualService",
            "metadata": {
                "name": activity_model.service_name,
                "namespace": activity_model.namespace,
            },
            "spec": {
                "hosts": [activity_model.host],
                "gateways": ["istio-system/istiogateway"],
                "http": activity_model.payload,
            },
        }

        payload = k8s_dynamic_client.client.sanitize_for_serialization(body)
        k8s_dynamic_client.server_side_apply(resource=resource, body=payload, field_manager="kubectl-client-side-apply")
        log_info(f"VirtualService {activity_model.service_name} created in namespace {activity_model.namespace}")


class DeleteKubernetesIstioVirtualServiceActivityModel(LaunchpadCLIBaseModel):
    """
    DeleteKubernetesIstioVirtualServiceActivityModel
    """

    namespace: str
    service_name: str


class DeleteKubernetesIstioVirtualServiceActivity(Activity):
    """
    DeleteKubernetesIstioVirtualServiceActivity
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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5, backoff_coefficient=2)

    @staticmethod
    @activity.defn(name="DeleteKubernetesIstioVirtualServiceActivity")
    async def defn(activity_model: DeleteKubernetesIstioVirtualServiceActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_dynamic_client = get_dynamic_client()
        resource = get_resource(
            dynamic_client=k8s_dynamic_client,
            kind=ResourceKindEnum.VirtualService,
            api_version="networking.istio.io/v1beta1",
        )

        k8s_dynamic_client.delete(
            resource=resource, name=activity_model.service_name, namespace=activity_model.namespace
        )

        log_info(f"VirtualService {activity_model.service_name} deleted in namespace {activity_model.namespace}")
