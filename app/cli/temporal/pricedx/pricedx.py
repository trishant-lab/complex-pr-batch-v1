from temporalio.client import WorkflowHandle

from app.cli.temporal.pricedx.models.pricedxSpec import PricedxSpec
from app.cli.workflowbase import ProductWorkflow
from app.core.cli_settings import WorkerQueues

ProductName = "pricedx"

class PricedxWorkflow(ProductWorkflow):
    """
    PricedxWorkflow class
    """

    @staticmethod
    async def onboard(schema: dict) -> None:
        """
        onboard method
        """
        from app.cli.temporal.pricedx.workflows.onboarding import PricedxOnboardingWorkflow
        from app.cli.temporal.starter import trigger_workflow

        await trigger_workflow(
            workflow_input=PricedxSpec(**schema),
            workflow=PricedxOnboardingWorkflow,
            queue=WorkerQueues.pricedx_onboarding,
        )

    @staticmethod
    async def deboard(schema: dict) -> None:
        """
        deprovision method
        """
        raise NotImplementedError

    @staticmethod
    async def get_workflow_handle(schema: dict) -> WorkflowHandle:
        """
        get_workflow_handle method
        """
        from app.cli.temporal.starter import get_workflow_handle
        from app.cli.temporal.pricedx.workflows.onboarding import PricedxOnboardingWorkflow

        return await get_workflow_handle(workflow_input=PricedxSpec(**schema), workflow=PricedxOnboardingWorkflow)

    @staticmethod
    def get_workflow_id(schema: dict) -> str:
        """
        Get the workflow id for the given schema
        """
        from app.cli.temporal.pricedx.workflows.onboarding import PricedxOnboardingWorkflow

        return PricedxOnboardingWorkflow.get_workflow_id(schema)
