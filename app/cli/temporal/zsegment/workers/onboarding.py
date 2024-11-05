import asyncio

from loguru import logger
from temporalio.worker import Worker
from temporalio.client import Client

from app.core.settings import AppSettings, get_settings
from app.cli.temporal.zsegment.workflows.onboarding import ZSegmentOnboardingWorkflow


async def zsegment_onboarding_worker() -> None:
    """
    Workflow worker for zsegment onboarding
    """
    config: AppSettings = get_settings()

    client = await Client.connect(config.temporal.dsn, namespace=config.temporal.namespace)

    logger.info("Starting zsegment onboarding worker...")

    worker: Worker = Worker(
        client,
        task_queue=config.zsegment.temporal_zsegment_onboarding_task_queue,
        workflows=[ZSegmentOnboardingWorkflow],
        activities=ZSegmentOnboardingWorkflow.get_activities(),
        debug_mode=True,
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(zsegment_onboarding_worker())
