from temporalio.client import WorkflowHandle

from app.cli.temporal.veritable.models.veritableSpec import VeritableSpec
from app.cli.workflowbase import ProductWorkflow
from app.core.cli_settings import WorkerQueues

ProductName = "veritable"


class VeritableWorkflow(ProductWorkflow):
    """
    VeritableWorkflow class
    """

    @staticmethod
    async def onboard(schema: dict) -> None:
        """
        onboard method
        """
        from app.cli.temporal.veritable.workflows.onboarding import VeritableOnboardingWorkflow
        from app.cli.temporal.starter import trigger_workflow

        await trigger_workflow(
            workflow_input=VeritableSpec(**schema),
            workflow=VeritableOnboardingWorkflow,
            queue=WorkerQueues.veritable_onboarding,
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
        from app.cli.temporal.veritable.workflows.onboarding import VeritableOnboardingWorkflow

        return await get_workflow_handle(workflow_input=VeritableSpec(**schema), workflow=VeritableOnboardingWorkflow)
