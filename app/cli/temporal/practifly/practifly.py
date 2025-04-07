from temporalio.client import WorkflowHandle

from app.cli.base_workflow import ProductWorkflow
from app.cli.temporal.practifly.models.practifly_spec import PractiflySpec
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
        from app.cli.temporal.models.deboard import DeboardWorkflowInput
        from app.cli.temporal.practifly.workflows.deprovisioning import PractiflyDeProvisioningWorkflow
        from app.cli.temporal.starter import trigger_workflow

        await trigger_workflow(
            workflow_input=DeboardWorkflowInput(**schema),
            workflow=PractiflyDeProvisioningWorkflow,
            queue=WorkerQueues.practifly_deboarding,
        )

    @staticmethod
    async def approve(schema: dict) -> None:
        """
        approve method
        """
        from app.cli.temporal.practifly.workflows.onboarding import PractiflyOnboardingWorkflow
        from app.cli.temporal.starter import get_workflow_handle

        handle = await get_workflow_handle(workflow_input=PractiflySpec(**schema), workflow=PractiflyOnboardingWorkflow)

        await handle.signal(PractiflyOnboardingWorkflow.approve)

    @staticmethod
    async def decline(schema: dict) -> None:
        """
        decline method
        """
        from app.cli.temporal.practifly.workflows.onboarding import PractiflyOnboardingWorkflow
        from app.cli.temporal.starter import get_workflow_handle

        handle = await get_workflow_handle(workflow_input=PractiflySpec(**schema), workflow=PractiflyOnboardingWorkflow)

        await handle.signal(PractiflyOnboardingWorkflow.decline)

    @staticmethod
    async def approve_deprovisioning(schema: dict) -> None:
        """
        approve_deprovisioning method
        """
        from app.cli.temporal.models.deboard import DeboardWorkflowInput
        from app.cli.temporal.practifly.workflows.deprovisioning import PractiflyDeProvisioningWorkflow
        from app.cli.temporal.starter import get_workflow_handle

        handle = await get_workflow_handle(
            workflow_input=DeboardWorkflowInput(**schema), workflow=PractiflyDeProvisioningWorkflow
        )

        await handle.signal(PractiflyDeProvisioningWorkflow.approve)

    @staticmethod
    async def deny_deprovisioning(schema: dict) -> None:
        """
        deny_deprovisioning method
        """
        from app.cli.temporal.models.deboard import DeboardWorkflowInput
        from app.cli.temporal.practifly.workflows.deprovisioning import PractiflyDeProvisioningWorkflow
        from app.cli.temporal.starter import get_workflow_handle

        handle = await get_workflow_handle(
            workflow_input=DeboardWorkflowInput(**schema), workflow=PractiflyDeProvisioningWorkflow
        )

        await handle.signal(PractiflyDeProvisioningWorkflow.decline)

    @staticmethod
    async def get_workflow_handle(schema: dict) -> WorkflowHandle:
        """
        get_workflow_handle method
        """
        from app.cli.temporal.practifly.workflows.onboarding import PractiflyOnboardingWorkflow
        from app.cli.temporal.starter import get_workflow_handle

        return await get_workflow_handle(workflow_input=PractiflySpec(**schema), workflow=PractiflyOnboardingWorkflow)

    @staticmethod
    def get_workflow_id(schema: dict) -> str:
        """
        Get the workflow id for the given schema
        """
        from app.cli.temporal.practifly.workflows.onboarding import PractiflyOnboardingWorkflow

        return PractiflyOnboardingWorkflow.get_workflow_id(schema)
