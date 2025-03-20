import asyncio

from loguru import logger
from temporalio.worker import Worker

from app.cli.temporal.core.connection import get_temporal_client
from app.core.settings import AppSettings, get_settings
from app.cli.temporal.pricedx.workflows.onboarding import PricedxOnboardingWorkflow

async def pricedx_onboarding_worker() -> None:
    """
    Workflow worker for pricedx onboarding
    """
    config: AppSettings = get_settings()

    client = await get_temporal_client()

    logger.info("Starting pricedx onboarding worker...")

    worker: Worker = Worker(
        client,
        task_queue=config.pricedx.temporal_pricedx_onboarding_task_queue,
        workflows=[PricedxOnboardingWorkflow],
        activities=PricedxOnboardingWorkflow.get_activities(),
        debug_mode=True,
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(pricedx_onboarding_worker())
