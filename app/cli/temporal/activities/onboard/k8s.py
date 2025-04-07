from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.activity_utils.onboard.k8s import trigger_provisioning_workflow
from app.cli.temporal.core.base import Activity
from app.cli.temporal.models.onboard import OnboardInfo


class ProvisioningK8SActivity(Activity):
    @staticmethod
    def get_timeout() -> timedelta:
        """
        @return:
        """
        return timedelta(seconds=10)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        @return:
        """
        return RetryPolicy(
            maximum_attempts=2,
            maximum_interval=timedelta(seconds=10),
            non_retryable_error_types=[],
        )

    @staticmethod
    @activity.defn(name="ProvisioningK8SActivity")
    async def defn(activity_input: OnboardInfo) -> None:
        """
        @param activity_input:
        @return:
        """
        await trigger_provisioning_workflow(activity_input.customer_id, activity_input.product)
