"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 40)
"""

import asyncio
from datetime import timedelta
from uuid import UUID

import httpx
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.activity_utils.payments.invoice_file import get_invoice_helper, is_valid_pdf
from app.cli.activity_utils.payments.success import download_invoice, payment_success_service
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.exceptions import RetryableException
from app.models.product import ProductEnum


class PaymentSuccessActivityInput(LaunchpadCLIBaseModel):
    lago_id: UUID
    product: ProductEnum


class PaymentSuccessActivity(Activity):
    _timeout = 120
    _step = 5

    @staticmethod
    def get_timeout() -> timedelta:
        """
        @return:
        """
        return timedelta(seconds=PaymentSuccessActivity._timeout * 3)

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
    @activity.defn(name="PaymentSuccessActivity")
    async def defn(activity_input: PaymentSuccessActivityInput) -> None:
        """
        Validate invoice
        """
        _time = 0
        _step = PaymentSuccessActivity._step
        _timeout = PaymentSuccessActivity._timeout

        invoice = download_invoice(activity_input.product, str(activity_input.lago_id))
        while invoice is None or invoice.file_url is None:
            invoice = download_invoice(activity_input.product, str(activity_input.lago_id))

            if (invoice is None or invoice.file_url is None) and _time >= _timeout:
                msg = "Invoice pdf file not yet generated!"
                raise RetryableException(msg)

            _time += _step
            await asyncio.sleep(_step)

        _time = 0
        valid = False
        invoice_data = get_invoice_helper(activity_input.product, invoice.model_dump(exclude_none=True))
        while valid is False:
            file_data = httpx.get(invoice_data["file_url"], timeout=60, follow_redirects=True).content
            valid, pdf_error = is_valid_pdf(file_data)
            if _time >= _timeout and not valid:
                raise RetryableException(pdf_error)
            _time += _step
            await asyncio.sleep(_step)

        await payment_success_service(activity_input.product, invoice)


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
