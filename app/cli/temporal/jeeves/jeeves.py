from temporalio.client import WorkflowHandle

from app.cli.base_workflow import ProductWorkflow
from app.cli.temporal.jeeves.models.jeeves_spec import JeevesSpec
from app.core.cli_settings import WorkerQueues

ProductName = "jeeves"


class JeevesWorkflow(ProductWorkflow):
    """
    JeevesWorkflow class
    """

    @staticmethod
    async def onboard(schema: dict) -> None:
        """
        onboard method
        """
        from app.cli.temporal.jeeves.workflows.onboarding import JeevesOnboardingWorkflow
        from app.cli.temporal.starter import trigger_workflow

        await trigger_workflow(
            workflow_input=JeevesSpec(**schema),
            workflow=JeevesOnboardingWorkflow,
            queue=WorkerQueues.jeeves_onboarding,
        )

    @staticmethod
    async def deboard(schema: dict) -> None:
        """
        deprovision method
        """
        from app.cli.temporal.jeeves.workflows.deprovisioning import JeevesDeProvisioningWorkflow
        from app.cli.temporal.models.deboard import DeboardWorkflowInput
        from app.cli.temporal.starter import trigger_workflow

        await trigger_workflow(
            workflow_input=DeboardWorkflowInput(**schema),
            workflow=JeevesDeProvisioningWorkflow,
            queue=WorkerQueues.jeeves_deboarding,
        )

    @staticmethod
    async def deploy(schema: dict) -> None:
        """
        deploy method
        """
        from app.cli.temporal.jeeves.workflows.onboarding import JeevesOnboardingWorkflow
        from app.cli.temporal.starter import trigger_workflow

        schema["is_deployment"] = True
        await trigger_workflow(
            workflow_input=JeevesSpec(**schema),
            workflow=JeevesOnboardingWorkflow,
            queue=WorkerQueues.jeeves_onboarding,
        )

    @staticmethod
    async def approve(schema: dict) -> None:
        """
        approve method
        """
        from app.cli.temporal.jeeves.workflows.onboarding import JeevesOnboardingWorkflow
        from app.cli.temporal.starter import get_workflow_handle

        handle = await get_workflow_handle(workflow_input=JeevesSpec(**schema), workflow=JeevesOnboardingWorkflow)

        await handle.signal(JeevesOnboardingWorkflow.approve)

    @staticmethod
    async def decline(schema: dict) -> None:
        """
        decline method
        """
        from app.cli.temporal.jeeves.workflows.onboarding import JeevesOnboardingWorkflow
        from app.cli.temporal.starter import get_workflow_handle

        handle = await get_workflow_handle(workflow_input=JeevesSpec(**schema), workflow=JeevesOnboardingWorkflow)

        await handle.signal(JeevesOnboardingWorkflow.decline)

    @staticmethod
    async def get_workflow_handle(schema: dict) -> WorkflowHandle:
        """
        get_workflow_handle method
        """
        from app.cli.temporal.jeeves.workflows.onboarding import JeevesOnboardingWorkflow
        from app.cli.temporal.starter import get_workflow_handle

        return await get_workflow_handle(workflow_input=JeevesSpec(**schema), workflow=JeevesOnboardingWorkflow)

    @staticmethod
    def get_workflow_id(schema: dict) -> str:
        """
        Get the workflow id for the given schema
        """
        from app.cli.temporal.jeeves.workflows.onboarding import JeevesOnboardingWorkflow

        return JeevesOnboardingWorkflow.get_workflow_id(schema)

    @staticmethod
    async def approve_deprovisioning(schema: dict) -> None:
        """
        approve_deprovisioning method
        """
        from app.cli.temporal.jeeves.workflows.deprovisioning import JeevesDeProvisioningWorkflow
        from app.cli.temporal.models.deboard import DeboardWorkflowInput
        from app.cli.temporal.starter import get_workflow_handle

        handle = await get_workflow_handle(
            workflow_input=DeboardWorkflowInput(**schema), workflow=JeevesDeProvisioningWorkflow
        )

        await handle.signal(JeevesDeProvisioningWorkflow.approve)

    @staticmethod
    async def deny_deprovisioning(schema: dict) -> None:
        """
        deny_deprovisioning method
        """
        from app.cli.temporal.jeeves.workflows.deprovisioning import JeevesDeProvisioningWorkflow
        from app.cli.temporal.models.deboard import DeboardWorkflowInput
        from app.cli.temporal.starter import get_workflow_handle

        handle = await get_workflow_handle(
            workflow_input=DeboardWorkflowInput(**schema), workflow=JeevesDeProvisioningWorkflow
        )

        await handle.signal(JeevesDeProvisioningWorkflow.decline)
