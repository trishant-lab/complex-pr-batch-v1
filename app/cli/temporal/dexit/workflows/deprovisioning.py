from collections.abc import Callable

from temporalio import workflow

from app.cli.temporal.core.base import Workflow
from app.cli.temporal.dexit.models.dexitSpec import DexitSpec

with workflow.unsafe.imports_passed_through():
    pass


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
    def get_workflow_id(cls: "Workflow", workflow_input: DexitSpec) -> str | None:
        """
        Return unique workflow id from workflow input, guarantees exactly one execution of workflow
        - Add combination of one or more fields from `workflow_input` to uniquely identify workflow
        """
        return f"de_provisioning_{workflow_input.tenant}"

    @workflow.run
    async def run(self: "Workflow", workflow_input: DexitSpec) -> None:
        """
        Entry point for workflow
        """
        pass
        # delete k8s service
        # await workflow.execute_activity(
        #     DeleteKubernetesServiceActivity.defn,
        #     arg=workflow_input,
        #     start_to_close_timeout=timedelta(seconds=120),
        #     retry_policy=DeleteKubernetesServiceActivity.get_retry_policy(),
        # )

        # # delete k8s virtual service
        # await workflow.execute_activity(
        #     DeleteKubernetesVirtualServiceActivity.defn,
        #     arg=workflow_input,
        #     start_to_close_timeout=timedelta(seconds=120),
        #     retry_policy=DeleteKubernetesVirtualServiceActivity.get_retry_policy(),
        # )

        # # delete provisioning job
        # await workflow.execute_activity(
        #     DeleteProvisioningJobActivity.defn,
        #     arg=workflow_input,
        #     start_to_close_timeout=timedelta(seconds=120),
        #     retry_policy=DeleteProvisioningJobActivity.get_retry_policy(),
        # )

        # # delete deployment
        # await workflow.execute_activity(
        #     DeleteDeploymentActivity.defn,
        #     arg=workflow_input,
        #     start_to_close_timeout=timedelta(seconds=120),
        #     retry_policy=DeleteDeploymentActivity.get_retry_policy(),
        # )

        # # delete config map
        # await workflow.execute_activity(
        #     DeleteConfigMapActivity.defn,
        #     arg=workflow_input,
        #     start_to_close_timeout=timedelta(seconds=120),
        #     retry_policy=DeleteConfigMapActivity.get_retry_policy(),
        # )

        # # drop ui bundles
        # await workflow.execute_activity(
        #     DropUIBundlesActivity.defn,
        #     arg=workflow_input,
        #     start_to_close_timeout=timedelta(seconds=120),
        #     retry_policy=DropUIBundlesActivity.get_retry_policy(),
        # )

        # # delete dns
        # await workflow.execute_activity(
        #     DeleteDNSActivity.defn,
        #     arg=workflow_input,
        #     start_to_close_timeout=timedelta(seconds=120),
        #     retry_policy=DeleteDNSActivity.get_retry_policy(),
        # )
