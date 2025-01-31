from temporalio.client import WorkflowHandle

from app.cli.temporal.practifly.models.practiflySpec import PractiflySpec
from app.cli.workflowbase import ProductWorkflow
from app.core.cli_settings import WorkerQueues

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
        from app.cli.temporal.practifly.workflows.onboarding import PractiflyOnboardingWorkflow
        from app.cli.temporal.starter import trigger_workflow

        await trigger_workflow(
            workflow_input=PractiflySpec(**schema),
            workflow=PractiflyOnboardingWorkflow,
            queue=WorkerQueues.practifly_onboarding,
        )

    @staticmethod
    async def deboard(schema: dict) -> None:
        """
        deprovision method
        """
        from app.cli.temporal.practifly.workflows.deprovisioning import PractiflyDeProvisioningWorkflow
        from app.cli.temporal.starter import trigger_workflow

        await trigger_workflow(
            workflow_input=PractiflySpec(**schema),
            workflow=PractiflyDeProvisioningWorkflow,
            queue=WorkerQueues.practifly_deboarding,
        )

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
    async def approve_deprovisioning(schema: dict) -> None:
        """
        approve_deprovisioning method
        """
        from app.cli.temporal.starter import get_workflow_handle
        from app.cli.temporal.practifly.workflows.deprovisioning import PractiflyDeProvisioningWorkflow

        handle = await get_workflow_handle(
            workflow_input=PractiflySpec(**schema), workflow=PractiflyDeProvisioningWorkflow
        )

        await handle.signal(PractiflyDeProvisioningWorkflow.approve)

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

    @staticmethod
    def get_workflow_id(schema: dict) -> str:
        """
        Get the workflow id for the given schema
        """
        from app.cli.temporal.practifly.workflows.onboarding import PractiflyOnboardingWorkflow

        return PractiflyOnboardingWorkflow.get_workflow_id(schema)
