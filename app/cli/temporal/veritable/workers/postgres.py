import asyncio

from loguru import logger
from temporalio.worker import Worker

from app.cli.temporal.core.connection import get_temporal_client
from app.core.settings import AppSettings, get_settings
from app.cli.temporal.veritable.workflows.postgres import VeritablePostgresSetupWorkflow


async def veritable_postgres_setup_worker():
    """
    Workflow worker for veritable onboarding
    """
    config: AppSettings = get_settings()

    client = await get_temporal_client()

    logger.info("Starting veritable postgres setup worker...")

    worker: Worker = Worker(
        client,
        task_queue=config.veritable.temporal_veritable_postgres_setup_task_queue,
        workflows=[VeritablePostgresSetupWorkflow],
        activities=VeritablePostgresSetupWorkflow.get_activities(),
        debug_mode=True
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(veritable_postgres_setup_worker())
