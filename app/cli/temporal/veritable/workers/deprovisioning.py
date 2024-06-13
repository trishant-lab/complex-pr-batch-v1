import asyncio

from loguru import logger
from temporalio.worker import Worker

from app.cli.temporal.core.connection import get_temporal_client
from app.core.settings import AppSettings, get_settings
from app.cli.temporal.veritable.workflows.deprovisioning import VeritableDeProvisioningWorkflow


async def veritable_deprovisioning_worker():
    """
    Workflow worker for veritable onboarding
    """
    config: AppSettings = get_settings()

    client = await get_temporal_client()

    logger.info("Starting veritable onboarding worker...")

    worker: Worker = Worker(
        client,
        task_queue=config.veritable.temporal_veritable_deboarding_task_queue,
        workflows=[VeritableDeProvisioningWorkflow],
        activities=VeritableDeProvisioningWorkflow.get_activities(),
        debug_mode=True
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(veritable_deprovisioning_worker())
