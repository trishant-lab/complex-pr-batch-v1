from temporalio.client import WorkflowHandle

from app.cli.temporal.hdp.models.hdpSpec import HDPSpec
from app.cli.workflowbase import ProductWorkflow
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
        from app.core.settings import HDPSettings, get_settings
        from app.cli.temporal.hdp.workflows.onboarding import HDPOnboardingWorkflow
        from app.cli.temporal.starter import trigger_workflow

        product_config: HDPSettings = get_settings().hdp
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
        from app.cli.temporal.starter import get_workflow_handle
        from app.cli.temporal.hdp.workflows.onboarding import HDPOnboardingWorkflow

        handle = await get_workflow_handle(workflow_input=HDPSpec(**schema), workflow=HDPOnboardingWorkflow)

        await handle.signal(HDPOnboardingWorkflow.approve)

    @staticmethod
    async def decline(schema: dict) -> None:
        """
        decline method
        """
        from app.cli.temporal.starter import get_workflow_handle
        from app.cli.temporal.hdp.workflows.onboarding import HDPOnboardingWorkflow

        handle = await get_workflow_handle(workflow_input=HDPSpec(**schema), workflow=HDPOnboardingWorkflow)

        await handle.signal(HDPOnboardingWorkflow.deny)

    @staticmethod
    async def get_workflow_handle(schema: dict) -> WorkflowHandle:
        """
        get_workflow_handle method
        """
        from app.cli.temporal.starter import get_workflow_handle
        from app.cli.temporal.hdp.workflows.onboarding import HDPOnboardingWorkflow

        return await get_workflow_handle(workflow_input=HDPSpec(**schema), workflow=HDPOnboardingWorkflow)
