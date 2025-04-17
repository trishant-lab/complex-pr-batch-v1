from datetime import timedelta

from kubernetes.dynamic.exceptions import NotFoundError
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.k8s_util import ResourceKindEnum, get_dynamic_client, get_resource
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_error, log_info

API_VERSION = "networking.istio.io/v1beta1"


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
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

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
            api_version=API_VERSION,
        )

        body = {
            "apiVersion": API_VERSION,
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
        k8s_dynamic_client.server_side_apply(
            resource=resource, body=payload, field_manager="kubectl-client-side-apply", force_conflicts=True
        )
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
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

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
            api_version=API_VERSION,
        )

        try:
            k8s_dynamic_client.delete(
                resource=resource, name=activity_model.service_name, namespace=activity_model.namespace
            )
        except NotFoundError:
            log_error(f"VirtualService {activity_model.service_name} not found in namespace {activity_model.namespace}")

        log_info(f"VirtualService {activity_model.service_name} deleted in namespace {activity_model.namespace}")
