import asyncio

from loguru import logger
from temporalio.worker import Worker

from app.cli.temporal.core.connection import get_temporal_client
from app.core.settings import AppSettings, get_settings
from app.cli.temporal.veritable.workflows.onboarding import VeritableOnboardingWorkflow


async def veritable_onboarding_worker() -> None:
    """
    Workflow worker for veritable onboarding
    """
    config: AppSettings = get_settings()

    client = await get_temporal_client()

    logger.info("Starting veritable onboarding worker...")

    worker: Worker = Worker(
        client,
        task_queue=config.veritable.temporal_veritable_onboarding_task_queue,
        workflows=[VeritableOnboardingWorkflow],
        activities=VeritableOnboardingWorkflow.get_activities(),
        debug_mode=True,
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(veritable_onboarding_worker())
