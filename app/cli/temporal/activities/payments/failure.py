from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.activity_utils.payments.failure import onboard_payment_failure, payment_failure
from app.cli.temporal.core.base import Activity
from app.cli.temporal.models.onboard import CustomerWorkflowInput, OnboardInfo


class PaymentFailureActivity(Activity):
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
        )

    @staticmethod
    @activity.defn(name="PaymentFailureActivity")
    async def defn(activity_input: CustomerWorkflowInput) -> None:
        """
        Retry payment failure
        """
        await payment_failure(activity_input.customer_id, activity_input.product)


class OnboardPaymentFailureActivity(Activity):
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
    @activity.defn(name="OnboardPaymentFailureActivity")
    async def defn(activity_input: OnboardInfo) -> None:
        """
        @param activity_input:
        @return:
        """
        await onboard_payment_failure(activity_input)
