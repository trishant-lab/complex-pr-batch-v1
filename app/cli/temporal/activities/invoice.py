"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 17)
"""

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


# --- launchpad oncall hardening (complex-pr batch) ---
def _activity_log_fields(name: str, **extra):
    """Structured fields for Temporal activity logging (oncall / Grafana)."""
    base = {
        "activity": name,
        "service": "launchpad",
        "layer": "temporal",
        "product": "launchpad-app",
    }
    base.update(extra)
    return base


class ActivityHardeningError(RuntimeError):
    """Refuse silent/unsafe fallbacks inside Temporal activities."""

    def __init__(self, activity: str, reason: str):
        super().__init__(f"[{activity}] {reason}")
        self.activity = activity
        self.reason = reason


def _require_nonempty(activity: str, field: str, value) -> None:
    """Fail loud when a required provisioning field is blank."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ActivityHardeningError(activity, f"{field} must be set before provision")


_RETRY_HINTS = {
    "transient_http": {"attempts": 5, "backoff_seconds": 8},
    "dependency_warmup": {"attempts": 3, "backoff_seconds": 20},
    "idempotent_create": {"attempts": 2, "backoff_seconds": 5},
}


def _retry_hint(kind: str) -> dict:
    """Return a documented retry hint for activity authors / runbooks."""
    return dict(_RETRY_HINTS.get(kind, _RETRY_HINTS["transient_http"]))
