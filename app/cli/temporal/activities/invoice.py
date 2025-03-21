import asyncio
from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.activity_utils.onboard.invoice import fetch_subscription_invoice
from app.cli.temporal.core.base import Activity
from app.cli.temporal.exceptions.onboard import InvoiceNotGeneratedException, InvoiceStatusPendingException
from app.cli.temporal.models.onboard import OnboardInfo
from app.models.billing_models import PaymentStatus


class FirstInvoicePollActivity(Activity):
    _timeout: int = 120
    _step: int = 5

    @staticmethod
    def get_timeout() -> timedelta:
        """
        @return:
        """
        return timedelta(seconds=FirstInvoicePollActivity._timeout * 1.5)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        @return:
        """
        return RetryPolicy(
            maximum_attempts=10,
            maximum_interval=timedelta(seconds=60),
        )

    @staticmethod
    @activity.defn(name="FirstInvoicePollActivity")
    async def defn(activity_input: OnboardInfo) -> OnboardInfo:
        """
        @param activity_input:
        @return:
        """
        _time: int = 0
        _timeout = FirstInvoicePollActivity._timeout
        _step = FirstInvoicePollActivity._step

        while activity_input.invoice is None:
            activity_input.invoice = fetch_subscription_invoice(activity_input)

            if activity_input.invoice is None and _time >= FirstInvoicePollActivity._timeout:
                raise InvoiceNotGeneratedException()

            _time += _step
            await asyncio.sleep(_step)

        return activity_input


class FirstInvoiceStatusPollActivity(Activity):
    _timeout: int = 120
    _step: int = 5

    @staticmethod
    def get_timeout() -> timedelta:
        """
        @return:
        """
        return timedelta(seconds=FirstInvoiceStatusPollActivity._timeout * 1.5)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        @return:
        """
        return RetryPolicy(
            maximum_attempts=10,
            maximum_interval=timedelta(seconds=60),
        )

    @staticmethod
    @activity.defn(name="FirstInvoiceStatusPollActivity")
    async def defn(activity_input: OnboardInfo) -> OnboardInfo:
        """
        @param activity_input:
        @return:
        """
        _time: int = 0
        _timeout = FirstInvoiceStatusPollActivity._timeout
        _step = FirstInvoiceStatusPollActivity._step

        activity_input.invoice = fetch_subscription_invoice(activity_input)

        while activity_input.invoice.payment_status == PaymentStatus.pending:
            activity_input.invoice = fetch_subscription_invoice(activity_input)

            if activity_input.invoice.payment_status == PaymentStatus.pending and _time >= _timeout:
                raise InvoiceStatusPendingException()

            _time += _step
            await asyncio.sleep(_step)

        return activity_input
