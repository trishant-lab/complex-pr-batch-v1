from collections.abc import Callable

import pydash
from temporalio import workflow

from app.cli.temporal.core.base import Workflow
from app.cli.temporal.models.deboard import DeboardWorkflowInput


@workflow.defn
class PenknifeDeProvisioningWorkflow(Workflow):
    """
    Penknife DeBoarding Workflow
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
        return f"de_provisioning_{pydash.get(workflow_input, 'tenant_id')}"

    @workflow.run
    async def run(self: "Workflow", workflow_input: DeboardWorkflowInput) -> None:
        """
        Entry point for workflow
        """
        pass
        # delete k8s service
        # await run_activity(
        #     DeleteKubernetesServiceActivity,
        #     arg=workflow_input,
        #     start_to_close_timeout=timedelta(seconds=120),
        # )

        # # delete k8s virtual service
        # await run_activity(
        #     DeleteKubernetesVirtualServiceActivity,
        #     arg=workflow_input,
        #     start_to_close_timeout=timedelta(seconds=120),
        # )

        # # delete provisioning job
        # await run_activity(
        #     DeleteProvisioningJobActivity,
        #     arg=workflow_input,
        #     start_to_close_timeout=timedelta(seconds=120),
        # )

        # # delete deployment
        # await run_activity(
        #     DeleteDeploymentActivity,
        #     arg=workflow_input,
        #     start_to_close_timeout=timedelta(seconds=120),
        # )

        # # delete config map
        # await run_activity(
        #     DeleteConfigMapActivity,
        #     arg=workflow_input,
        #     start_to_close_timeout=timedelta(seconds=120),
        # )

        # # drop ui bundles
        # await run_activity(
        #     DropUIBundlesActivity,
        #     arg=workflow_input,
        #     start_to_close_timeout=timedelta(seconds=120),
        # )

        # # delete dns
        # await run_activity(
        #     DeleteDNSActivity,
        #     arg=workflow_input,
        #     start_to_close_timeout=timedelta(seconds=120),
        # )

        # # delete vm scraper
        # await run_activity(
        #     DeleteVMScraperActivity,
        #     arg=workflow_input,
        #     start_to_close_timeout=timedelta(seconds=120),
        # )

        # # delete redis namespace
        # await run_activity(
        #     DeleteRedisNamespace,
        #     arg=workflow_input,
        #     start_to_close_timeout=timedelta(seconds=120),
        # )

        # # # delete stateful set
        # # await run_activity(
        # #     DeleteStatefulSetActivity,
        # #     arg=workflow_input,
        # #     start_to_close_timeout=timedelta(seconds=120),
        # # )

        # # delete keycloak client or realm
        # await run_activity(
        #     DeleteKeycloakRealmActivity,
        #     arg=workflow_input,
        #     start_to_close_timeout=timedelta(seconds=120),
        # )
