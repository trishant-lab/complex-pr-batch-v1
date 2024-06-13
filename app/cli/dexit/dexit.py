from app.cli.dexit.models.dexitSpec import DexitSpec
from app.cli.workflowbase import ProductWorkflow

ProductName = "dexit"


class DexitWorkflow(ProductWorkflow):
    """
    VeritableWorkflow class
    """

    @staticmethod
    async def onboard(schema: dict):
        """
        onboard method
        """
        from app.core.settings import DexitSettings, get_settings
        from app.cli.temporal.dexit.workflows.onboarding import DexitOnboardingWorkflow
        from app.cli.temporal.dexit.starter import trigger_workflow

        product_config: DexitSettings = get_settings().dexit
        await trigger_workflow(
            workflow_input=DexitSpec(**schema),
            workflow=DexitOnboardingWorkflow,
            queue=product_config.temporal_dexit_onboarding_task_queue
        )

    @staticmethod
    async def deboard(schema: dict):
        """
        deprovision method
        """
        from app.core.settings import DexitSettings, get_settings
        from app.cli.temporal.dexit.starter import trigger_workflow
        from app.cli.temporal.dexit.workflows.deprovisioning import DexitDeProvisioningWorkflow

        product_config: DexitSettings = get_settings().dexit
        await trigger_workflow(
            workflow_input=DexitSpec(**schema),
            workflow=DexitDeProvisioningWorkflow,
            queue=product_config.temporal_dexit_deboarding_task_queue
        )

    @staticmethod
    async def approve(schema: dict):
        """
        approve method
        """
        from app.cli.temporal.dexit.starter import get_workflow_handle
        from app.cli.temporal.dexit.workflows.onboarding import DexitOnboardingWorkflow

        handle = await get_workflow_handle(workflow_input=DexitSpec(**schema),workflow=DexitOnboardingWorkflow)

        await handle.signal(DexitOnboardingWorkflow.approve)
