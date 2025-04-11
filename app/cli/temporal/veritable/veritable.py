from temporalio.client import WorkflowHandle

from app.cli.base_workflow import ProductWorkflow
from app.cli.temporal.veritable.models.veritable_spec import VeritableSpec
from app.core.cli_settings import WorkerQueues

ProductName = "veritable"


class VeritableWorkflow(ProductWorkflow):
    """
    VeritableWorkflow class
    """

    @staticmethod
    async def onboard(schema: dict) -> None:
        """
        onboard method
        """
        from app.cli.temporal.starter import trigger_workflow
        from app.cli.temporal.veritable.workflows.onboarding import VeritableOnboardingWorkflow

        await trigger_workflow(
            workflow_input=VeritableSpec(**schema),
            workflow=VeritableOnboardingWorkflow,
            queue=WorkerQueues.veritable_onboarding,
        )

    @staticmethod
    async def deboard(schema: dict) -> None:
        """
        deprovision method
        """
        from app.cli.temporal.models.deboard import DeboardWorkflowInput
        from app.cli.temporal.starter import trigger_workflow
        from app.cli.temporal.veritable.workflows.deprovisioning import VeritableDeProvisioningWorkflow

        await trigger_workflow(
            workflow_input=DeboardWorkflowInput(**schema),
            workflow=VeritableDeProvisioningWorkflow,
            queue=WorkerQueues.veritable_deboarding,
        )

    @staticmethod
    async def deploy(schema: dict) -> None:
        """
        deploy method
        """
        from app.cli.temporal.starter import trigger_workflow
        from app.cli.temporal.veritable.workflows.deployment import VeritableDeploymentWorkflow

        await trigger_workflow(
            workflow_input=VeritableSpec(**schema),
            workflow=VeritableDeploymentWorkflow,
            queue=WorkerQueues.veritable_deployment,
        )

    @staticmethod
    async def get_workflow_handle(schema: dict) -> WorkflowHandle:
        """
        get_workflow_handle method
        """
        from app.cli.temporal.starter import get_workflow_handle
        from app.cli.temporal.veritable.workflows.onboarding import VeritableOnboardingWorkflow

        return await get_workflow_handle(workflow_input=VeritableSpec(**schema), workflow=VeritableOnboardingWorkflow)

    @staticmethod
    def get_workflow_id(schema: dict) -> str:
        """
        Get the workflow id for the given schema
        """
        from app.cli.temporal.veritable.workflows.onboarding import VeritableOnboardingWorkflow

        return VeritableOnboardingWorkflow.get_workflow_id(schema)

    @staticmethod
    async def approve_deprovisioning(schema: dict) -> None:
        """
        approve_deprovisioning method
        """
        from app.cli.temporal.models.deboard import DeboardWorkflowInput
        from app.cli.temporal.starter import get_workflow_handle
        from app.cli.temporal.veritable.workflows.deprovisioning import VeritableDeProvisioningWorkflow

        handle = await get_workflow_handle(
            workflow_input=DeboardWorkflowInput(**schema), workflow=VeritableDeProvisioningWorkflow
        )

        await handle.signal(VeritableDeProvisioningWorkflow.approve)

    @staticmethod
    async def deny_deprovisioning(schema: dict) -> None:
        """
        deny_deprovisioning method
        """
        from app.cli.temporal.models.deboard import DeboardWorkflowInput
        from app.cli.temporal.starter import get_workflow_handle
        from app.cli.temporal.veritable.workflows.deprovisioning import VeritableDeProvisioningWorkflow

        handle = await get_workflow_handle(
            workflow_input=DeboardWorkflowInput(**schema), workflow=VeritableDeProvisioningWorkflow
        )

        await handle.signal(VeritableDeProvisioningWorkflow.decline)
