import asyncio

from loguru import logger
from temporalio.worker import Worker
from temporalio.client import Client

from app.core.settings import AppSettings, get_settings
from app.cli.temporal.veritable.workflows.postgres import VeritablePostgresSetupWorkflow


async def veritable_postgres_setup_worker():
    """
    Workflow worker for veritable onboarding
    """
    config: AppSettings = get_settings()

    client = await Client.connect(config.temporal.dsn, namespace=config.temporal.namespace)

    logger.info("Starting veritable postgres setup worker...")

    worker: Worker = Worker(
        client,
        task_queue=config.temporal_veritable_postgres_setup_task_queue,
        workflows=[VeritablePostgresSetupWorkflow],
        activities=VeritablePostgresSetupWorkflow.get_activities(),
        debug_mode=True
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(veritable_postgres_setup_worker())
