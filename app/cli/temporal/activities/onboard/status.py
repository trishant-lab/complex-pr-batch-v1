import asyncio
from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.activity_utils.onboard.onboard_info import (
    get_customer_onboard_info,
    get_operator_status,
    update_operator_status,
)
from app.cli.temporal.core.base import Activity
from app.cli.temporal.models.onboard import CustomerWorkflowInput, OnboardInfo
from app.models.tenant import TenantStatusEnum


class OnboardStatusActivity(Activity):
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
    @activity.defn(name="OnboardStatusActivity")
    async def defn(activity_input: CustomerWorkflowInput) -> OnboardInfo:
        """
        @param activity_input:
        @return:
        """
        return await get_customer_onboard_info(activity_input.customer_id)


class PollOnboardStatusActivity(Activity):
    _timeout = 600
    _step = 5

    @staticmethod
    def get_timeout() -> timedelta:
        """
        @return:
        """
        return timedelta(seconds=PollOnboardStatusActivity._timeout * 1.5)

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
    @activity.defn(name="PollOnboardStatusActivity")
    async def defn(activity_input: CustomerWorkflowInput) -> OnboardInfo:
        """
        @param activity_input:
        @return:
        """
        _time = 0
        _step = PollOnboardStatusActivity._step
        _timeout = PollOnboardStatusActivity._timeout

        activity_input = await get_customer_onboard_info(activity_input.customer_id)

        while activity_input.onboard_status == TenantStatusEnum.Provisioning:
            activity_input.onboard_status = await get_operator_status(activity_input.customer_id)

            if activity_input.onboard_status == TenantStatusEnum.Provisioning and _time >= _timeout:
                activity_input.onboard_status = TenantStatusEnum.ProvisioningFailed
                await update_operator_status(
                    activity_input.customer_id,
                    activity_input.onboard_status,
                    Exception("Operator status polling timed out!"),
                )

            _time += _step
            await asyncio.sleep(_step)

        return activity_input
