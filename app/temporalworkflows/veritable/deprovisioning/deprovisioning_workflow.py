from dataclasses import dataclass
from datetime import timedelta

from loguru import logger
from temporalio import workflow
from temporalio.common import RetryPolicy

from app.temporalworkflows.veritable.deprovisioning.deprovisioning_activity import delete_all_resources


@dataclass
class DeprovisioningWorkflowInput:
    tenant: str


@workflow.defn(name="de_provisioning_workflow", sandboxed=False)
class DeprovisioningWorkflow:
    @workflow.run
    async def run(self, workflow_input: DeprovisioningWorkflowInput) -> None:
        """
        Deprovisioning workflow
        """
        logger.info(f"Starting Deprovisioning Workflow for Veritable tenant: {workflow_input.tenant}")

        retry_policy: RetryPolicy = RetryPolicy(
            backoff_coefficient=2.0,
            maximum_attempts=1,
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=60),
        )

        # delete k8s resources
        await workflow.execute_activity(
            delete_all_resources,
            workflow_input.tenant,
            retry_policy=retry_policy,
            start_to_close_timeout=timedelta(seconds=300),
        )
