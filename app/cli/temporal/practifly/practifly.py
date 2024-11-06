from temporalio.client import WorkflowHandle

from app.cli.temporal.practifly.models.practiflySpec import PractiflySpec
from app.cli.workflowbase import ProductWorkflow

ProductName = "practifly"


class PractiflyWorkflow(ProductWorkflow):
    """
    PractiflyWorkflow class
    """

    @staticmethod
    async def onboard(schema: dict) -> None:
        """
        onboard method
        """
        from app.core.settings import PractiflySettings, get_settings
        from app.cli.temporal.practifly.workflows.onboarding import PractiflyOnboardingWorkflow
        from app.cli.temporal.starter import trigger_workflow

        product_config: PractiflySettings = get_settings().practifly
        await trigger_workflow(
            workflow_input=PractiflySpec(**schema),
            workflow=PractiflyOnboardingWorkflow,
            queue=product_config.temporal_practifly_onboarding_task_queue,
        )

    @staticmethod
    async def deboard(schema: dict) -> None:
        """
        deprovision method
        """
        raise NotImplementedError

    @staticmethod
    async def approve(schema: dict) -> None:
        """
        approve method
        """
        from app.cli.temporal.starter import get_workflow_handle
        from app.cli.temporal.practifly.workflows.onboarding import PractiflyOnboardingWorkflow

        handle = await get_workflow_handle(workflow_input=PractiflySpec(**schema), workflow=PractiflyOnboardingWorkflow)

        await handle.signal(PractiflyOnboardingWorkflow.approve)

    @staticmethod
    async def decline(schema: dict) -> None:
        """
        decline method
        """
        from app.cli.temporal.starter import get_workflow_handle
        from app.cli.temporal.practifly.workflows.onboarding import PractiflyOnboardingWorkflow

        handle = await get_workflow_handle(workflow_input=PractiflySpec(**schema), workflow=PractiflyOnboardingWorkflow)

        await handle.signal(PractiflyOnboardingWorkflow.deny)

    @staticmethod
    async def get_workflow_handle(schema: dict) -> WorkflowHandle:
        """
        get_workflow_handle method
        """
        from app.cli.temporal.starter import get_workflow_handle
        from app.cli.temporal.practifly.workflows.onboarding import PractiflyOnboardingWorkflow

        return await get_workflow_handle(workflow_input=PractiflySpec(**schema), workflow=PractiflyOnboardingWorkflow)
