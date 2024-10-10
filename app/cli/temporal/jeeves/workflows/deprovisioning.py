from collections.abc import Callable
from datetime import timedelta

from temporalio import workflow

from app.cli.temporal.core.base import Workflow
from app.cli.temporal.jeeves.activities.deprovisioning import (
    DeleteKubernetesServiceActivity,
    DeleteKubernetesVirtualServiceActivity,
    DeleteProvisioningJobActivity,
    DeleteDeploymentActivity,
    DeleteConfigMapActivity,
    # DeletePVCActivity,
    DropUIBundlesActivity,
    DeleteDNSActivity,
    DeleteVMScraperActivity,
    DeleteStatefulSetActivity,
)
from app.cli.jeeves.jeeves import JeevesSpec

with workflow.unsafe.imports_passed_through():
    pass


@workflow.defn
class JeevesDeProvisioningWorkflow(Workflow):
    """
    Jeeves DeBoarding Workflow
    """

    @staticmethod
    def get_activities() -> list[type[Callable]]:
        """
        Return list of activities used in the workflow
        """
        return [
            DeleteKubernetesServiceActivity.defn,
            DeleteKubernetesVirtualServiceActivity.defn,
            DeleteProvisioningJobActivity.defn,
            DeleteDeploymentActivity.defn,
            DeleteConfigMapActivity.defn,
            DropUIBundlesActivity.defn,
            DeleteDNSActivity.defn,
            DeleteVMScraperActivity.defn,
            DeleteStatefulSetActivity.defn,
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", workflow_input: JeevesSpec) -> str | None:
        """
        Return unique workflow id from workflow input, guarantees exactly one execution of workflow
        - Add combination of one or more fields from `workflow_input` to uniquely identify workflow
        """
        return f"de_provisioning_{workflow_input.tenant}"

    @workflow.run
    async def run(self: "Workflow", workflow_input: JeevesSpec) -> None:
        """
        Entry point for workflow
        """
        # delete k8s service
        await workflow.execute_activity(
            DeleteKubernetesServiceActivity.defn,
            arg=workflow_input,
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=DeleteKubernetesServiceActivity.get_retry_policy(),
        )

        # delete k8s virtual service
        await workflow.execute_activity(
            DeleteKubernetesVirtualServiceActivity.defn,
            arg=workflow_input,
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=DeleteKubernetesVirtualServiceActivity.get_retry_policy(),
        )

        # delete provisioning job
        await workflow.execute_activity(
            DeleteProvisioningJobActivity.defn,
            arg=workflow_input,
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=DeleteProvisioningJobActivity.get_retry_policy(),
        )

        # delete deployment
        await workflow.execute_activity(
            DeleteDeploymentActivity.defn,
            arg=workflow_input,
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=DeleteDeploymentActivity.get_retry_policy(),
        )

        # delete config map
        await workflow.execute_activity(
            DeleteConfigMapActivity.defn,
            arg=workflow_input,
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=DeleteConfigMapActivity.get_retry_policy(),
        )

        # # delete pvc
        # await workflow.execute_activity(
        #     DeletePVCActivity.defn,
        #     arg=workflow_input,
        #     start_to_close_timeout=timedelta(seconds=120),
        #     retry_policy=DeletePVCActivity.get_retry_policy(),
        # )

        # drop ui bundles
        await workflow.execute_activity(
            DropUIBundlesActivity.defn,
            arg=workflow_input,
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=DropUIBundlesActivity.get_retry_policy(),
        )

        # delete dns
        await workflow.execute_activity(
            DeleteDNSActivity.defn,
            arg=workflow_input,
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=DeleteDNSActivity.get_retry_policy(),
        )

        # delete vm scraper
        await workflow.execute_activity(
            DeleteVMScraperActivity.defn,
            arg=workflow_input,
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=DeleteVMScraperActivity.get_retry_policy(),
        )

        # delete stateful set
        await workflow.execute_activity(
            DeleteStatefulSetActivity.defn,
            arg=workflow_input,
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=DeleteStatefulSetActivity.get_retry_policy(),
        )
