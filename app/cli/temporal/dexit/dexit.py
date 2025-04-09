from temporalio.client import WorkflowHandle

from app.cli.base_workflow import ProductWorkflow
from app.cli.temporal.dexit.models.dexit_spec import DexitSpec
from app.core.cli_settings import WorkerQueues

ProductName = "dexit"


class DexitWorkflow(ProductWorkflow):
    """
    DexitWorkflow class
    """

    @staticmethod
    async def onboard(schema: dict) -> None:
        """
        onboard method
        """
        from app.cli.temporal.dexit.workflows.onboarding import DexitOnboardingWorkflow
        from app.cli.temporal.starter import trigger_workflow

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
        from app.cli.temporal.dexit.workflows.deprovisioning import DexitDeProvisioningWorkflow
        from app.cli.temporal.models.deboard import DeboardWorkflowInput
        from app.cli.temporal.starter import trigger_workflow

        await trigger_workflow(
            workflow_input=DeboardWorkflowInput(**schema),
            workflow=DexitDeProvisioningWorkflow,
            queue=WorkerQueues.dexit_deboarding,
        )

    @staticmethod
    async def approve(schema: dict) -> None:
        """
        approve method
        """
        from app.cli.temporal.dexit.workflows.onboarding import DexitOnboardingWorkflow
        from app.cli.temporal.starter import get_workflow_handle

        handle = await get_workflow_handle(workflow_input=DexitSpec(**schema), workflow=DexitOnboardingWorkflow)

        await handle.signal(DexitOnboardingWorkflow.approve)

    @staticmethod
    async def decline(schema: dict) -> None:
        """
        decline method
        """
        from app.cli.temporal.dexit.workflows.onboarding import DexitOnboardingWorkflow
        from app.cli.temporal.starter import get_workflow_handle

        handle = await get_workflow_handle(workflow_input=DexitSpec(**schema), workflow=DexitOnboardingWorkflow)

        await handle.signal(DexitOnboardingWorkflow.decline)

    @staticmethod
    async def get_workflow_handle(schema: dict) -> WorkflowHandle:
        """
        get_workflow_handle method
        """
        from app.cli.temporal.dexit.workflows.onboarding import DexitOnboardingWorkflow
        from app.cli.temporal.starter import get_workflow_handle

        return await get_workflow_handle(workflow_input=DexitSpec(**schema), workflow=DexitOnboardingWorkflow)

    @staticmethod
    def get_workflow_id(schema: dict) -> str:
        """
        Get the workflow id for the given schema
        """
        from app.cli.temporal.dexit.workflows.onboarding import DexitOnboardingWorkflow

        return DexitOnboardingWorkflow.get_workflow_id(schema)
