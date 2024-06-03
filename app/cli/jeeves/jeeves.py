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
