from temporalio.client import WorkflowHandle

from app.cli.temporal.zsegment.models.zsegmentSpec import ZSegmentSpec
from app.cli.workflowbase import ProductWorkflow
from app.core.cli_settings import WorkerQueues

ProductName = "zsegment"


class ZSegmentWorkflow(ProductWorkflow):
    """
    ZSegmentWorkflow class
    """

    @staticmethod
    async def onboard(schema: dict) -> None:
        """
        onboard method
        """
        from app.cli.temporal.zsegment.workflows.onboarding import ZSegmentOnboardingWorkflow
        from app.cli.temporal.starter import trigger_workflow

        await trigger_workflow(
            workflow_input=ZSegmentSpec(**schema),
            workflow=ZSegmentOnboardingWorkflow,
            queue=WorkerQueues.zsegment_onboarding,
        )

    @staticmethod
    async def deboard(schema: dict) -> None:
        """
        deprovision method
        """
        raise NotImplementedError("ZSegment deprovisioning is not implemented")

    @staticmethod
    async def approve(schema: dict) -> None:
        """
        approve method
        """
        from app.cli.temporal.starter import get_workflow_handle
        from app.cli.temporal.zsegment.workflows.onboarding import ZSegmentOnboardingWorkflow

        handle = await get_workflow_handle(workflow_input=ZSegmentSpec(**schema), workflow=ZSegmentOnboardingWorkflow)

        await handle.signal(ZSegmentOnboardingWorkflow.approve)

    @staticmethod
    async def decline(schema: dict) -> None:
        """
        decline method
        """
        from app.cli.temporal.starter import get_workflow_handle
        from app.cli.temporal.zsegment.workflows.onboarding import ZSegmentOnboardingWorkflow

        handle = await get_workflow_handle(workflow_input=ZSegmentSpec(**schema), workflow=ZSegmentOnboardingWorkflow)

        await handle.signal(ZSegmentOnboardingWorkflow.deny)

    @staticmethod
    async def get_workflow_handle(schema: dict) -> WorkflowHandle:
        """
        get_workflow_handle method
        """
        from app.cli.temporal.starter import get_workflow_handle
        from app.cli.temporal.zsegment.workflows.onboarding import ZSegmentOnboardingWorkflow

        return await get_workflow_handle(workflow_input=ZSegmentSpec(**schema), workflow=ZSegmentOnboardingWorkflow)
