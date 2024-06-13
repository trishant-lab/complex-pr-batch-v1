import asyncio

from loguru import logger
from temporalio.worker import Worker
from temporalio.client import Client

from app.core.settings import AppSettings, get_settings
from app.cli.temporal.dexit.workflows.deprovisioning import DexitDeProvisioningWorkflow


async def dexit_deprovisioning_worker():
    """
    Workflow worker for dexit onboarding
    """
    config: AppSettings = get_settings()

    client = await Client.connect(config.temporal.dsn, namespace=config.temporal.namespace)

    logger.info("Starting dexit de-provisioning worker...")

    worker: Worker = Worker(
        client,
        task_queue=config.dexit.temporal_dexit_deboarding_task_queue,
        workflows=[DexitDeProvisioningWorkflow],
        activities=DexitDeProvisioningWorkflow.get_activities(),
        debug_mode=True
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(dexit_deprovisioning_worker())
