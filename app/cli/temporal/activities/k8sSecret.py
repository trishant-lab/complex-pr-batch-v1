from datetime import timedelta
from temporalio import activity
from temporalio.common import RetryPolicy
from kubernetes.client import V1Secret, V1ObjectMeta
from app.cli.k8s_util import ResourceKindEnum, get_dynamic_client, get_resource
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_info


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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)

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
        k8s_dynamic_client.server_side_apply(
            resource=k8s_secret_resource, body=payload, field_manager="kubectl-client-side-apply"
        )

        log_info(f"Secret {activity_model.name} created successfully")
