from app.cli.jeeves.models.jeevesSpec import JeevesSpec
from app.cli.workflowbase import ProductWorkflow

ProductName = "jeeves"


class JeevesWorkflow(ProductWorkflow):
    """
    VeritableWorkflow class
    """

    @staticmethod
    async def onboard(schema: dict):
        """
        onboard method
        """
        from app.core.settings import JeevesSettings, get_settings
        from app.cli.temporal.jeeves.workflows.onboarding import JeevesOnboardingWorkflow
        from app.cli.temporal.jeeves.starter import trigger_workflow

        product_config: JeevesSettings = get_settings().jeeves
        await trigger_workflow(
            workflow_input=JeevesSpec(**schema),
            workflow=JeevesOnboardingWorkflow,
            queue=product_config.temporal_jeeves_onboarding_task_queue
        )

    @staticmethod
    async def deboard(schema: dict):
        """
        deprovision method
        """
        from app.core.settings import JeevesSettings, get_settings
        from app.cli.temporal.jeeves.starter import trigger_workflow
        from app.cli.temporal.jeeves.workflows.deprovisioning import JeevesDeProvisioningWorkflow

        product_config: JeevesSettings = get_settings().jeeves
        await trigger_workflow(
            workflow_input=JeevesSpec(**schema),
            workflow=JeevesDeProvisioningWorkflow,
            queue=product_config.temporal_jeeves_deboarding_task_queue
        )

    @staticmethod
    async def approve(schema: dict):
        """
        approve method
        """
        from app.cli.temporal.jeeves.starter import get_workflow_handle
        from app.cli.temporal.jeeves.workflows.onboarding import JeevesOnboardingWorkflow

        handle = await get_workflow_handle(workflow_input=JeevesSpec(**schema),workflow=JeevesOnboardingWorkflow)

        await handle.signal(JeevesOnboardingWorkflow.approve)

    @staticmethod
    async def decline(schema: dict):
        """
        decline method
        """
        from app.cli.temporal.jeeves.starter import get_workflow_handle
        from app.cli.temporal.jeeves.workflows.onboarding import JeevesOnboardingWorkflow

        handle = await get_workflow_handle(workflow_input=JeevesSpec(**schema),workflow=JeevesOnboardingWorkflow)

        await handle.signal(JeevesOnboardingWorkflow.deny)
