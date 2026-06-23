from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.log import log_error
from kubernetes.dynamic.exceptions import NotFoundError

from datetime import timedelta
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_info


VMPODSCRAPE_API_VERSION = "operator.victoriametrics.com/v1beta1"


class VMPodScrapperActivityModel(LaunchpadCLIBaseModel):
    """
    VMPodScrapperActivityModel
    """

    namespace: str
    name: str
    app: str
    path: str
    interval: str
    app_match_values: list[str] | None = None


class VMPodScrapperActivity(Activity):
    """
    VMPodScrapperActivity
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
        Retry policy for the activity
        """
        return RetryPolicy(
            maximum_attempts=5,
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
        )

    @staticmethod
    @activity.defn(name="VMPodScrapperActivity")
    async def defn(activity_model: VMPodScrapperActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_dynamic_client = get_dynamic_client()

        resource = get_resource(
            dynamic_client=k8s_dynamic_client,
            kind=ResourceKindEnum.VMPodScrape,
            api_version=VMPODSCRAPE_API_VERSION,
        )

        body = {
            "apiVersion": VMPODSCRAPE_API_VERSION,
            "kind": ResourceKindEnum.VMPodScrape.value,
            "metadata": {
                "name": activity_model.name,
                "namespace": activity_model.namespace,
            },
            "spec": {
                "namespaceSelector": {"matchNames": [activity_model.namespace]},
                "podMetricsEndpoints": [
                    {"path": activity_model.path, "port": "http", "interval": activity_model.interval}
                ],
                "selector": (
                    {
                        "matchExpressions": [
                            {"key": "app", "operator": "In", "values": activity_model.app_match_values}
                        ]
                    }
                    if activity_model.app_match_values
                    else {"matchLabels": {"app": activity_model.app}}
                ),
            },
        }

        payload = k8s_dynamic_client.client.sanitize_for_serialization(body)
        k8s_dynamic_client.server_side_apply(
            resource=resource,
            body=payload,
            field_manager="kubectl-client-side-apply",
            force_conflicts=True,
        )
        log_info(f"VMPodScrapper created in namespace {activity_model.namespace}")


class VMPodScrapperDeletionActivityModel(LaunchpadCLIBaseModel):
    """
    VMPodScrapperDeletionActivityModel
    """

    namespace: str
    name: str


class VMPodScrapperDeletionActivity(Activity):
    """
    VMPodScrapperDeletionActivity
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
    @activity.defn(name="VMPodScrapperDeletionActivity")
    async def defn(activity_model: VMPodScrapperDeletionActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_dynamic_client = get_dynamic_client()

        resource = get_resource(
            dynamic_client=k8s_dynamic_client,
            kind=ResourceKindEnum.VMPodScrape,
            api_version=VMPODSCRAPE_API_VERSION,
        )
        try:
            k8s_dynamic_client.delete(resource=resource, name=activity_model.name, namespace=activity_model.namespace)
        except NotFoundError:
            log_error(f"VMPodScrapper {activity_model.name} not found in namespace {activity_model.namespace}")

        log_info(f"VMPodScrapperDeletion deleted in namespace {activity_model.namespace}")
