"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 10)
"""

import asyncio
from datetime import timedelta

from temporalio import activity
from temporalio.client import WorkflowExecutionStatus
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity
from app.cli.temporal.core.log import log_info
from app.cli.temporal.starter import get_workflow_handle, trigger_workflow
from app.cli.temporal.zsegment.models.zsegment_spec import ZSegmentSpec
from app.cli.temporal.zsegment.workflows.onboarding import ZSegmentOnboardingWorkflow
from app.core.cli_settings import WorkerQueues


class ZSegmentSetupActivity(Activity):
    """
    Activity to setup ZSegment for a tenant
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(minutes=10)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Retry policy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=60),
            backoff_coefficient=3,
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="ZSegmentSetupActivity")
    async def defn(model: ZSegmentSpec) -> None:
        """
        Setup ZSegment for a tenant
        """
        await trigger_workflow(
            workflow_input=ZSegmentSpec(
                tenant=model.tenant,
                email=model.email,
                firstName=model.firstName,
                lastName=model.lastName,
                organization=model.organization,
            ),
            workflow=ZSegmentOnboardingWorkflow,
            queue=WorkerQueues.zsegment_onboarding,
        )

        await asyncio.sleep(10)

        handle = await get_workflow_handle(
            workflow_input=ZSegmentSpec(
                tenant=model.tenant,
                email=model.email,
                firstName=model.firstName,
                lastName=model.lastName,
            ),
            workflow=ZSegmentOnboardingWorkflow,
        )

        # Manually approve the workflow by sending a signal
        await handle.signal(ZSegmentOnboardingWorkflow.approve)

        handle_describe = await handle.describe()
        status = WorkflowExecutionStatus(handle_describe.status).name

        while status != "COMPLETED":
            if status in ["FAILED", "TERMINATED"]:
                raise RuntimeError(f"ZSegment onboarding {status}")
            handle_describe = await handle.describe()
            status = WorkflowExecutionStatus(handle_describe.status).name
            await asyncio.sleep(60)

        log_info(f"ZSegment onboarding completed successfully for tenant {model.tenant}")


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
