from loguru import logger
from temporalio.client import Client

from app.core.settings import AppSettings, get_settings
from app.temporalworkflows.veritable.deprovisioning.deprovisioning_workflow import DeprovisioningWorkflow, \
    DeprovisioningWorkflowInput


async def trigger_veritable_deprovisioning_workflow(tenant: str) -> None:
    """
    Trigger the veritable deprovisioning workflow
    :param tenant:
    :return:
    """
    config: AppSettings = get_settings()
    client = await Client.connect(config.temporal_dsn, namespace=config.temporal_namespace)

    await client.start_workflow(
        DeprovisioningWorkflow.run,
        DeprovisioningWorkflowInput(tenant=tenant),
        id="veritable_deprovisioning_workflow",
        task_queue=config.temporal_veritable_deprovisioning_task_queue,
    )
    logger.info(f"Veritable deprovisioning workflow triggered for tenant {tenant}")

