from temporalio.client import WorkflowHandle

from app.cli.base_workflow import ProductWorkflow
from app.cli.temporal.pricedx.models.pricedx_spec import PricedxSpec
from app.core.cli_settings import WorkerQueues

ProductName = "pricedx"


class PricedxWorkflow(ProductWorkflow):
    """
    PricedxWorkflow class
    """

    @staticmethod
    async def onboard(schema: dict) -> None:
        """
        onboard method
        """
        from app.cli.temporal.pricedx.workflows.onboarding import PricedxOnboardingWorkflow
        from app.cli.temporal.starter import trigger_workflow

        await trigger_workflow(
            workflow_input=PricedxSpec(**schema),
            workflow=PricedxOnboardingWorkflow,
            queue=WorkerQueues.pricedx_onboarding,
        )

    @staticmethod
    async def deboard(schema: dict) -> None:
        """
        deprovision method
        """
        from app.cli.temporal.models.deboard import DeboardWorkflowInput
        from app.cli.temporal.pricedx.workflows.deprovisioning import PricedxDeProvisioningWorkflow
        from app.cli.temporal.starter import trigger_workflow

        await trigger_workflow(
            workflow_input=DeboardWorkflowInput(**schema),
            workflow=PricedxDeProvisioningWorkflow,
            queue=WorkerQueues.pricedx_deboarding,
        )

    @staticmethod
    async def deploy(schema: dict) -> None:
        """
        deploy method
        """
        raise NotImplementedError("Deploy is not implemented for Pricedx")

    @staticmethod
    async def approve(schema: dict) -> None:
        """
        approve method
        """
        from app.cli.temporal.pricedx.workflows.onboarding import PricedxOnboardingWorkflow
        from app.cli.temporal.starter import get_workflow_handle

        handle = await get_workflow_handle(workflow_input=PricedxSpec(**schema), workflow=PricedxOnboardingWorkflow)

        await handle.signal(PricedxOnboardingWorkflow.approve)

    @staticmethod
    async def decline(schema: dict) -> None:
        """
        decline method
        """
        from app.cli.temporal.pricedx.workflows.onboarding import PricedxOnboardingWorkflow
        from app.cli.temporal.starter import get_workflow_handle

        handle = await get_workflow_handle(workflow_input=PricedxSpec(**schema), workflow=PricedxOnboardingWorkflow)

        await handle.signal(PricedxOnboardingWorkflow.decline)

    @staticmethod
    async def approve_deprovisioning(schema: dict) -> None:
        """
        approve_deprovisioning method
        """
        from app.cli.temporal.models.deboard import DeboardWorkflowInput
        from app.cli.temporal.pricedx.workflows.deprovisioning import PricedxDeProvisioningWorkflow
        from app.cli.temporal.starter import get_workflow_handle

        handle = await get_workflow_handle(
            workflow_input=DeboardWorkflowInput(**schema), workflow=PricedxDeProvisioningWorkflow
        )

        await handle.signal(PricedxDeProvisioningWorkflow.approve)

    @staticmethod
    async def deny_deprovisioning(schema: dict) -> None:
        """
        deny_deprovisioning method
        """
        from app.cli.temporal.models.deboard import DeboardWorkflowInput
        from app.cli.temporal.pricedx.workflows.deprovisioning import PricedxDeProvisioningWorkflow
        from app.cli.temporal.starter import get_workflow_handle

        handle = await get_workflow_handle(
            workflow_input=DeboardWorkflowInput(**schema), workflow=PricedxDeProvisioningWorkflow
        )

        await handle.signal(PricedxDeProvisioningWorkflow.decline)

    @staticmethod
    async def get_workflow_handle(schema: dict) -> WorkflowHandle:
        """
        get_workflow_handle method
        """
        from app.cli.temporal.pricedx.workflows.onboarding import PricedxOnboardingWorkflow
        from app.cli.temporal.starter import get_workflow_handle

        return await get_workflow_handle(workflow_input=PricedxSpec(**schema), workflow=PricedxOnboardingWorkflow)

    @staticmethod
    def get_workflow_id(schema: dict) -> str:
        """
        Get the workflow id for the given schema
        """
        from app.cli.temporal.pricedx.workflows.onboarding import PricedxOnboardingWorkflow

        return PricedxOnboardingWorkflow.get_workflow_id(schema)

    @staticmethod
    async def space_provision(schema: dict) -> None:
        """
        space_provision method
        """
        raise NotImplementedError
