from temporalio.client import WorkflowHandle

from app.cli.base_workflow import ProductWorkflow
from app.cli.temporal.zsegment.models.zsegment_spec import ZSegmentSpec
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
        from app.cli.temporal.starter import trigger_workflow
        from app.cli.temporal.zsegment.workflows.onboarding import ZSegmentOnboardingWorkflow

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

        await handle.signal(ZSegmentOnboardingWorkflow.decline)

    @staticmethod
    async def get_workflow_handle(schema: dict) -> WorkflowHandle:
        """
        get_workflow_handle method
        """
        from app.cli.temporal.starter import get_workflow_handle
        from app.cli.temporal.zsegment.workflows.onboarding import ZSegmentOnboardingWorkflow

        return await get_workflow_handle(workflow_input=ZSegmentSpec(**schema), workflow=ZSegmentOnboardingWorkflow)

    @staticmethod
    def get_workflow_id(schema: dict) -> str:
        """
        Get the workflow id for the given schema
        """
        from app.cli.temporal.zsegment.workflows.onboarding import ZSegmentOnboardingWorkflow

        return ZSegmentOnboardingWorkflow.get_workflow_id(schema)
    

    @staticmethod
    async def deploy(schema: dict) -> None:
        """
        Deploy a product
        """
        raise NotImplementedError("ZSegment deployment is not implemented")