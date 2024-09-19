import asyncio

from loguru import logger
from temporalio.worker import Worker
from temporalio.client import Client

from app.cli.temporal.penknife.workflows.onboarding import PenknifeOnboardingWorkflow
from app.core.settings import AppSettings, get_settings


async def jeeves_onboarding_worker() -> None:
    """
    Workflow worker for jeeves onboarding
    """
    config: AppSettings = get_settings()

    client = await Client.connect(config.temporal.dsn, namespace=config.temporal.namespace)

    logger.info("Starting jeeves onboarding worker...")

    worker: Worker = Worker(
        client,
        task_queue=config.jeeves.temporal_jeeves_onboarding_task_queue,
        workflows=[PenknifeOnboardingWorkflow],
        activities=PenknifeOnboardingWorkflow.get_activities(),
        debug_mode=True,
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(jeeves_onboarding_worker())