from temporalio.client import WorkflowHandle

from app.cli.temporal.penknife.models.penknifespec import PenknifeSpec
from app.cli.workflowbase import ProductWorkflow
from app.core.cli_settings import WorkerQueues


ProductName = "penknife"


class PenknifeWorkflow(ProductWorkflow):
    """
    PenknifeWorkflow class
    """

    @staticmethod
    async def onboard(schema: dict) -> None:
        """
        onboard method
        """
        from app.core.settings import PenknifeSettings, get_settings
        from app.cli.temporal.penknife.workflows.onboarding import PenknifeOnboardingWorkflow
        from app.cli.temporal.starter import trigger_workflow

        product_config: PenknifeSettings = get_settings().penknife
        await trigger_workflow(
            workflow_input=PenknifeSpec(**schema),
            workflow=PenknifeOnboardingWorkflow,
            queue=WorkerQueues.penknife_onboarding,
        )

    @staticmethod
    async def deboard(schema: dict) -> None:
        """
        deprovision method
        """
        from app.core.settings import PenknifeSettings, get_settings
        from app.cli.temporal.starter import trigger_workflow
        from app.cli.temporal.penknife.workflows.deprovisioning import PenknifeDeProvisioningWorkflow

        product_config: PenknifeSettings = get_settings().penknife
        await trigger_workflow(
            workflow_input=PenknifeSpec(**schema),
            workflow=PenknifeDeProvisioningWorkflow,
            queue=WorkerQueues.penknife_deboarding,
        )

    @staticmethod
    async def approve(schema: dict) -> None:
        """
        approve method
        """
        from app.cli.temporal.starter import get_workflow_handle
        from app.cli.temporal.penknife.workflows.onboarding import PenknifeOnboardingWorkflow

        handle = await get_workflow_handle(workflow_input=PenknifeSpec(**schema), workflow=PenknifeOnboardingWorkflow)

        await handle.signal(PenknifeOnboardingWorkflow.approve)

    @staticmethod
    async def decline(schema: dict) -> None:
        """
        decline method
        """
        from app.cli.temporal.starter import get_workflow_handle
        from app.cli.temporal.penknife.workflows.onboarding import PenknifeOnboardingWorkflow

        handle = await get_workflow_handle(workflow_input=PenknifeSpec(**schema), workflow=PenknifeOnboardingWorkflow)

        await handle.signal(PenknifeOnboardingWorkflow.deny)

    @staticmethod
    async def get_workflow_handle(schema: dict) -> WorkflowHandle:
        """
        get_workflow_handle method
        """
        from app.cli.temporal.starter import get_workflow_handle
        from app.cli.temporal.penknife.workflows.onboarding import PenknifeOnboardingWorkflow

        return await get_workflow_handle(workflow_input=PenknifeSpec(**schema), workflow=PenknifeOnboardingWorkflow)
