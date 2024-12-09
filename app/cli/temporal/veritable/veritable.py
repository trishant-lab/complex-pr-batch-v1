from temporalio.client import WorkflowHandle

from app.cli.temporal.veritable.models.veritableSpec import VeritableSpec
from app.cli.workflowbase import ProductWorkflow

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
        from app.core.settings import VeritableSettings, get_settings
        from app.cli.temporal.veritable.workflows.onboarding import VeritableOnboardingWorkflow
        from app.cli.temporal.starter import trigger_workflow

        product_config: VeritableSettings = get_settings().veritable
        await trigger_workflow(
            workflow_input=VeritableSpec(**schema),
            workflow=VeritableOnboardingWorkflow,
            queue=product_config.temporal_veritable_onboarding_task_queue,
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
