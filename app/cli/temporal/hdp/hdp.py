from temporalio.client import WorkflowHandle

from app.cli.base_workflow import ProductWorkflow
from app.cli.temporal.hdp.models.hdp_spec import HDPSpec
from app.core.cli_settings import WorkerQueues

ProductName = "hdp"


class HdpWorkflow(ProductWorkflow):
    """
    HdpWorkflow class
    """

    @staticmethod
    async def onboard(schema: dict) -> None:
        """
        onboard method
        """
        from app.cli.temporal.hdp.workflows.onboarding import HDPOnboardingWorkflow
        from app.cli.temporal.starter import trigger_workflow

        await trigger_workflow(
            workflow_input=HDPSpec(**schema),
            workflow=HDPOnboardingWorkflow,
            queue=WorkerQueues.hdp_onboarding,
        )

    @staticmethod
    async def deboard(schema: dict) -> None:
        """
        deprovision method
        """
        raise NotImplementedError("Deboarding is not implemented for HDP")

    @staticmethod
    async def approve(schema: dict) -> None:
        """
        approve method
        """
        from app.cli.temporal.hdp.workflows.onboarding import HDPOnboardingWorkflow
        from app.cli.temporal.starter import get_workflow_handle

        handle = await get_workflow_handle(workflow_input=HDPSpec(**schema), workflow=HDPOnboardingWorkflow)

        await handle.signal(HDPOnboardingWorkflow.approve)

    @staticmethod
    async def decline(schema: dict) -> None:
        """
        decline method
        """
        from app.cli.temporal.hdp.workflows.onboarding import HDPOnboardingWorkflow
        from app.cli.temporal.starter import get_workflow_handle

        handle = await get_workflow_handle(workflow_input=HDPSpec(**schema), workflow=HDPOnboardingWorkflow)

        await handle.signal(HDPOnboardingWorkflow.deny)

    @staticmethod
    async def get_workflow_handle(schema: dict) -> WorkflowHandle:
        """
        get_workflow_handle method
        """
        from app.cli.temporal.hdp.workflows.onboarding import HDPOnboardingWorkflow
        from app.cli.temporal.starter import get_workflow_handle

        return await get_workflow_handle(workflow_input=HDPSpec(**schema), workflow=HDPOnboardingWorkflow)

    @staticmethod
    def get_workflow_id(schema: dict) -> str:
        """
        Get the workflow id for the given schema
        """
        from app.cli.temporal.hdp.workflows.onboarding import HDPOnboardingWorkflow

        return HDPOnboardingWorkflow.get_workflow_id(schema)
