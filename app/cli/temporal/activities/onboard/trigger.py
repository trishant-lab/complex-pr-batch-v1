from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity
from app.cli.temporal.models.onboard import CustomerWorkflowInput


class OnboardWorkflowTriggerActivity(Activity):
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
    @activity.defn(name="OnboardWorkflowTriggerActivity")
    async def defn(activity_input: CustomerWorkflowInput) -> None:
        """
        @param activity_input:
        @return:
        """
        from app.cli.activity_utils.onboard.trigger import trigger_onboarding_workflow

        await trigger_onboarding_workflow(activity_input)
