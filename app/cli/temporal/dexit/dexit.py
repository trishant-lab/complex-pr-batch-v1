from temporalio.client import WorkflowHandle

from app.cli.temporal.dexit.models.dexitSpec import DexitSpec
from app.cli.workflowbase import ProductWorkflow
from app.core.cli_settings import WorkerQueues

ProductName = "dexit"


class DexitWorkflow(ProductWorkflow):
    """
    VeritableWorkflow class
    """

    @staticmethod
    async def onboard(schema: dict) -> None:
        """
        onboard method
        """
        from app.core.settings import DexitSettings, get_settings
        from app.cli.temporal.dexit.workflows.onboarding import DexitOnboardingWorkflow
        from app.cli.temporal.starter import trigger_workflow

        product_config: DexitSettings = get_settings().dexit
        await trigger_workflow(
            workflow_input=DexitSpec(**schema),
            workflow=DexitOnboardingWorkflow,
            queue=WorkerQueues.dexit_onboarding,
        )

    @staticmethod
    async def deboard(schema: dict) -> None:
        """
        deprovision method
        """
        from app.core.settings import DexitSettings, get_settings
        from app.cli.temporal.starter import trigger_workflow
        from app.cli.temporal.dexit.workflows.deprovisioning import DexitDeProvisioningWorkflow

        product_config: DexitSettings = get_settings().dexit
        await trigger_workflow(
            workflow_input=DexitSpec(**schema),
            workflow=DexitDeProvisioningWorkflow,
            queue=WorkerQueues.dexit_deboarding,
        )

    @staticmethod
    async def approve(schema: dict) -> None:
        """
        approve method
        """
        from app.cli.temporal.starter import get_workflow_handle
        from app.cli.temporal.dexit.workflows.onboarding import DexitOnboardingWorkflow

        handle = await get_workflow_handle(workflow_input=DexitSpec(**schema), workflow=DexitOnboardingWorkflow)

        await handle.signal(DexitOnboardingWorkflow.approve)

    @staticmethod
    async def decline(schema: dict) -> None:
        """
        decline method
        """
        from app.cli.temporal.starter import get_workflow_handle
        from app.cli.temporal.dexit.workflows.onboarding import DexitOnboardingWorkflow

        handle = await get_workflow_handle(workflow_input=DexitSpec(**schema), workflow=DexitOnboardingWorkflow)

        await handle.signal(DexitOnboardingWorkflow.decline)

    @staticmethod
    async def get_workflow_handle(schema: dict) -> WorkflowHandle:
        """
        get_workflow_handle method
        """
        from app.cli.temporal.starter import get_workflow_handle
        from app.cli.temporal.dexit.workflows.onboarding import DexitOnboardingWorkflow

        return await get_workflow_handle(workflow_input=DexitSpec(**schema), workflow=DexitOnboardingWorkflow)
