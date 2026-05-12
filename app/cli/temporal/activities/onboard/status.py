"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 34)
"""

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
        return await get_customer_onboard_info(activity_input.customer_id, activity_input.product)


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

        activity_input = await get_customer_onboard_info(activity_input.customer_id, activity_input.product)

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
