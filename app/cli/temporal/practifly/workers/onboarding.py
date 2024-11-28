import asyncio

from loguru import logger
from temporalio.worker import Worker
from temporalio.client import Client

from app.cli.temporal.practifly.workflows.onboarding import PractiflyOnboardingWorkflow
from app.core.settings import AppSettings, get_settings


async def practifly_onboarding_worker() -> None:
    """
    Workflow worker for practifly onboarding
    """
    config: AppSettings = get_settings()

    client = await Client.connect(config.temporal.dsn, namespace=config.temporal.namespace)

    logger.info("Starting practifly onboarding worker...")

    worker: Worker = Worker(
        client,
        task_queue=config.practifly.temporal_practifly_onboarding_task_queue,
        workflows=[PractiflyOnboardingWorkflow],
        activities=PractiflyOnboardingWorkflow.get_activities(),
        debug_mode=True,
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(practifly_onboarding_worker())
