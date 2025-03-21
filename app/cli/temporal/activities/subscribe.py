from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.activity_utils.onboard.subscription import create_lago_subscription, terminate_failed_subscription
from app.cli.temporal.core.base import Activity
from app.cli.temporal.models.onboard import OnboardInfo


class SubscriptionActivity(Activity):
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
    @activity.defn(name="SubscriptionActivity")
    async def defn(activity_input: OnboardInfo) -> None:
        """
        @param activity_input:
        @return:
        """
        create_lago_subscription(activity_input)


class SubscriptionCleanupActivity(Activity):
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
    @activity.defn(name="SubscriptionCleanupActivity")
    async def defn(activity_input: OnboardInfo) -> None:
        """
        @param activity_input:
        @return:
        """
        await terminate_failed_subscription(activity_input)
