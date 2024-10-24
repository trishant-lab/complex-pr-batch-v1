from datetime import timedelta
from temporalio import activity
from temporalio.common import RetryPolicy
from kubernetes.client import V1Namespace, V1ObjectMeta

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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)

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
