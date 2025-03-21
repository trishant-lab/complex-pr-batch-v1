from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.activity_utils.payments.enterprise_check import is_enterprise_plan
from app.cli.temporal.core.base import Activity
from app.cli.temporal.models.webhooks.invoice import InvoiceWebhookEvent


class CheckEnterpriseActivity(Activity):
    @staticmethod
    def get_timeout() -> timedelta:
        """
        @return:
        """
        return timedelta(minutes=3)

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
    @activity.defn(name="CheckEnterpriseActivity")
    async def defn(activity_input: InvoiceWebhookEvent) -> bool:
        """
        check if customer is in enterprise plan
        """
        return is_enterprise_plan(activity_input.model_dump(exclude_none=True))
