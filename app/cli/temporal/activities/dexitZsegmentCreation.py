from datetime import timedelta
import asyncio

from temporalio import activity
from temporalio.api.enums.v1 import WorkflowExecutionStatus
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity
from app.cli.temporal.core.log import log_info
from app.cli.temporal.starter import get_workflow_handle, trigger_workflow
from app.cli.temporal.zsegment.models.zsegmentSpec import ZSegmentSpec
from app.cli.temporal.zsegment.workflows.onboarding import ZSegmentOnboardingWorkflow
from app.core.cli_settings import WorkerQueues


@activity.defn
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
                firstName=model.first_name,
                lastName=model.last_name,
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
                firstName=model.first_name,
                lastName=model.last_name,
            ),
            workflow=ZSegmentOnboardingWorkflow,
        )

        # Manually approve the workflow by sending a signal
        await handle.signal(ZSegmentOnboardingWorkflow.approve)

        handle_describe = await handle.describe()
        status = WorkflowExecutionStatus.Name(handle_describe.status)

        while status != "COMPLETED":
            if status in ["FAILED", "TERMINATED"]:
                raise Exception(f"ZSegment onboarding {status}")
            handle_describe = await handle.describe()
            status = WorkflowExecutionStatus.Name(handle_describe.status)
            await asyncio.sleep(60)

        log_info(f"ZSegment onboarding completed successfully for tenant {model.tenant}")
