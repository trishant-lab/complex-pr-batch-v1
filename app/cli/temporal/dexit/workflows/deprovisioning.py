from collections.abc import Callable

import pydash
from temporalio import workflow

from app.cli.temporal.core.base import Workflow
from app.cli.temporal.models.deboard import DeboardWorkflowInput


@workflow.defn
class DexitDeProvisioningWorkflow(Workflow):
    """
    Dexit DeBoarding Workflow
    """

    @staticmethod
    def get_activities() -> list[type[Callable]]:
        """
        Return list of activities used in the workflow
        """
        return []

    @classmethod
    def get_workflow_id(cls: "Workflow", workflow_input: DeboardWorkflowInput) -> str | None:
        """
        Return unique workflow id from workflow input, guarantees exactly one execution of workflow
        - Add combination of one or more fields from `workflow_input` to uniquely identify workflow
        """
        return f"dexit_deprovisioning_workflow_{pydash.get(workflow_input, 'tenant_name')}"

    @workflow.run
    async def run(self: "Workflow", workflow_input: DeboardWorkflowInput) -> None:
        """
        Entry point for workflow
        """
        pass
        # delete k8s service
        # await run_activity(
        #     activity=DeleteKubernetesServiceActivity,
        #     arg=workflow_input,
        #     start_to_close_timeout=timedelta(seconds=120),
        # )

        # # delete k8s virtual service
        # await run_activity(
        #     activity=DeleteKubernetesVirtualServiceActivity,
        #     arg=workflow_input,
        #     start_to_close_timeout=timedelta(seconds=120),
        # )

        # # delete provisioning job
        # await run_activity(
        #     activity=DeleteProvisioningJobActivity,
        #     arg=workflow_input,
        #     start_to_close_timeout=timedelta(seconds=120),
        # )

        # # delete deployment
        # await run_activity(
        #     activity=DeleteDeploymentActivity,
        #     arg=workflow_input,
        #     start_to_close_timeout=timedelta(seconds=120),
        # )

        # # delete config map
        # await run_activity(
        #     activity=DeleteConfigMapActivity,
        #     arg=workflow_input,
        #     start_to_close_timeout=timedelta(seconds=120),
        # )

        # # drop ui bundles
        # await run_activity(
        #     activity=DropUIBundlesActivity,
        #     arg=workflow_input,
        #     start_to_close_timeout=timedelta(seconds=120),
        # )

        # # delete dns
        # await run_activity(
        #     activity=DeleteDNSActivity,
        #     arg=workflow_input,
        #     start_to_close_timeout=timedelta(seconds=120),
        # )
