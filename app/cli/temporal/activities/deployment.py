from temporalio import activity
from temporalio.common import RetryPolicy

from datetime import timedelta
from kubernetes.dynamic.exceptions import NotFoundError
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.k8s_util import ResourceKindEnum, get_dynamic_client, get_resource
from app.cli.temporal.core.log import log_info, log_error


class DeploymentDeletionActivityModel(LaunchpadCLIBaseModel):
    """
    DeploymentDeletionActivityModel
    """

    namespace: str
    name: str


class DeploymentDeletionActivity(Activity):
    """
    DeploymentDeletionActivity
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
        return RetryPolicy(initial_interval=timedelta(seconds=10), maximum_attempts=5, backoff_coefficient=3)

    @staticmethod
    @activity.defn(name="DeploymentDeletionActivity")
    async def defn(activity_model: DeploymentDeletionActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_dynamic_client = get_dynamic_client()
        resource = get_resource(
            dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Deployment, api_version="apps/v1"
        )

        try:
            k8s_dynamic_client.delete(resource=resource, name=activity_model.name, namespace=activity_model.namespace)
        except NotFoundError as e:
            log_error(
                f"DeploymentDeletion failed to delete deployment {activity_model.name} "
                f"in namespace {activity_model.namespace}: {e}"
            )

        log_info(f"DeploymentDeletion deleted in namespace {activity_model.namespace}")
