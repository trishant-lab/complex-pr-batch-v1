import asyncio

from loguru import logger
from temporalio.worker import Worker
from temporalio.client import Client

from app.core.settings import AppSettings, get_settings
from app.cli.temporal.veritable.workflows.onboarding import VeritableOnboardingWorkflow


async def veritable_onboarding_worker():
    """
    Workflow worker for veritable onboarding
    """
    config: AppSettings = get_settings()

    client = await Client.connect(config.temporal.dsn, namespace=config.temporal.namespace)

    logger.info("Starting veritable onboarding worker...")

    worker: Worker = Worker(
        client,
        task_queue=config.veritable.temporal_veritable_onboarding_task_queue,
        workflows=[VeritableOnboardingWorkflow],
        activities=VeritableOnboardingWorkflow.get_activities(),
        debug_mode=True
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(veritable_onboarding_worker())
