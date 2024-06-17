from app.cli.temporal.veritable.starter import trigger_workflow
from app.cli.temporal.veritable.workflows.deprovisioning import VeritableDeProvisioningWorkflow
from app.cli.temporal.veritable.workflows.onboarding import VeritableOnboardingWorkflow
from app.cli.veritable.models.VeritableSpec import VeritableSpec
from app.cli.workflowbase import ProductWorkflow
from app.core.settings import get_settings, VeritableSettings

ProductName: str = "veritable"
OnepasswordVaultName: str = "practifly"
OnepasswordItemName: str = "veritable-tenant-config-{environment}"


class VeritableWorkflow(ProductWorkflow):
    """
    VeritableWorkflow class
    """

    @staticmethod
    async def onboard(schema: dict) -> None:
        """
        onboard method
        """
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
        product_config: VeritableSettings = get_settings().veritable
        await trigger_workflow(
            workflow_input=VeritableSpec(**schema),
            workflow=VeritableDeProvisioningWorkflow,
            queue=product_config.temporal_veritable_deboarding_task_queue,
        )
