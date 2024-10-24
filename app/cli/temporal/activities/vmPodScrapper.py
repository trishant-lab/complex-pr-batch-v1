from datetime import timedelta
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum

from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_info


class VMPodScrapperActivityModel(LaunchpadCLIBaseModel):
    """
    VMPodScrapperActivityModel
    """

    namespace: str
    name: str
    app: str
    path: str
    interval: str


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
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
        )

    @staticmethod
    @activity.defn(name="VMPodScrapperActivity")
    async def defn(activity_model: VMPodScrapperActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_dynamic_client = get_dynamic_client()

        resource = get_resource(ResourceKindEnum.VMPodScrape, activity_model.namespace, activity_model.name)

        body = {
            "apiVersion": "operator.victoriametrics.com/v1beta1",
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
                "selector": {"matchLabels": {"app": activity_model.app}},
            },
        }

        payload = k8s_dynamic_client.client.sanitize_for_serialization(body)
        resource.server_side_apply(body=payload, field_manager="kubectl-client-side-apply", force_conflicts=True)
        log_info(f"VMPodScrapper created in namespace {activity_model.namespace}")
