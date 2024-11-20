import asyncio

from loguru import logger
from temporalio.worker import Worker

from app.cli.temporal.core.connection import get_temporal_client
from app.core.settings import AppSettings, get_settings
from app.cli.temporal.practifly.workflows.deprovisioning import PractiflyDeProvisioningWorkflow


async def practifly_deprovisioning_worker() -> None:
    """
    Workflow worker for practifly deprovisioning
    """
    config: AppSettings = get_settings()

    client = await get_temporal_client()

    logger.info("Starting practifly deprovisioning worker...")

    worker: Worker = Worker(
        client,
        task_queue=config.practifly.temporal_practifly_deboarding_task_queue,
        workflows=[PractiflyDeProvisioningWorkflow],
        activities=PractiflyDeProvisioningWorkflow.get_activities(),
        debug_mode=True,
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(practifly_deprovisioning_worker())
