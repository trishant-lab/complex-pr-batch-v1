from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.activity_utils.onboard.failure import onboard_failure
from app.cli.temporal.core.base import Activity
from app.cli.temporal.models.onboard import CustomerWorkflowInput


class OnboardFailureMailActivity(Activity):
    @staticmethod
    def get_timeout() -> timedelta:
        """
        @return:
        """
        return timedelta(seconds=30)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        @return:
        """
        return RetryPolicy(
            maximum_attempts=4,
            maximum_interval=timedelta(seconds=10),
            non_retryable_error_types=["NonRetryableException"],
        )

    @staticmethod
    @activity.defn(name="OnboardFailureMailActivity")
    async def defn(activity_input: CustomerWorkflowInput) -> None:
        """
        @param activity_input:
        @return:
        """
        await onboard_failure(activity_input)
