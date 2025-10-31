from temporalio.client import WorkflowHandle

from app.cli.base_workflow import ProductWorkflow
from app.cli.temporal.muspell.models.muspellSpec import MuspellArchiveSpec
from app.core.cli_settings import WorkerQueues

ProductName = "muspell"


class MuspellArchiveWorkflow(ProductWorkflow):
    """
    MuspellArchiveWorkflow class
    """

    @staticmethod
    async def onboard(schema: dict) -> None:
        """
        onboard method
        """
        from app.cli.temporal.muspell.workflows.onboarding import MuspellOnboardingWorkflow
        from app.cli.temporal.starter import trigger_workflow

        await trigger_workflow(
            workflow_input=MuspellArchiveSpec(**schema),
            workflow=MuspellOnboardingWorkflow,
            queue=WorkerQueues.muspell_onboarding,
        )

    @staticmethod
    async def deboard(schema: dict) -> None:
        """
        deprovision method
        """
        raise NotImplementedError("Deboarding is not implemented for Muspell Archive")

    @staticmethod
    async def deploy(schema: dict) -> None:
        """
        deploy method
        """
        raise NotImplementedError("Deploy is not implemented for Muspell Archive")

    @staticmethod
    async def approve(schema: dict) -> None:
        """
        approve method
        """
        from app.cli.temporal.muspell.workflows.onboarding import MuspellOnboardingWorkflow
        from app.cli.temporal.starter import get_workflow_handle

        handle = await get_workflow_handle(
            workflow_input=MuspellArchiveSpec(**schema), workflow=MuspellOnboardingWorkflow
        )

        await handle.signal(MuspellOnboardingWorkflow.approve)

    @staticmethod
    async def decline(schema: dict) -> None:
        """
        decline method
        """
        from app.cli.temporal.muspell.workflows.onboarding import MuspellOnboardingWorkflow
        from app.cli.temporal.starter import get_workflow_handle

        handle = await get_workflow_handle(
            workflow_input=MuspellArchiveSpec(**schema), workflow=MuspellOnboardingWorkflow
        )

        await handle.signal(MuspellOnboardingWorkflow.deny)

    @staticmethod
    async def get_workflow_handle(schema: dict) -> WorkflowHandle:
        """
        get_workflow_handle method
        """
        from app.cli.temporal.muspell.workflows.onboarding import MuspellOnboardingWorkflow
        from app.cli.temporal.starter import get_workflow_handle

        return await get_workflow_handle(
            workflow_input=MuspellArchiveSpec(**schema), workflow=MuspellOnboardingWorkflow
        )

    @staticmethod
    def get_workflow_id(schema: dict) -> str:
        """
        Get the workflow id for the given schema
        """
        from app.cli.temporal.muspell.workflows.onboarding import MuspellOnboardingWorkflow

        return MuspellOnboardingWorkflow.get_workflow_id(schema)

    @staticmethod
    async def space_provision(schema: dict) -> None:
        """
        space_provision method
        """
        raise NotImplementedError
