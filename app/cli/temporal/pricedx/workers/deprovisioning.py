import asyncio

from loguru import logger
from temporalio.worker import Worker

from app.cli.temporal.core.connection import get_temporal_client
from app.core.settings import AppSettings, get_settings
from app.cli.temporal.pricedx.workflows.deprovisioning import PricedxDeProvisioningWorkflow

async def pricedx_deprovisioning_worker() -> None:
    """
    Workflow worker for pricedx deprovisioning
    """
    config: AppSettings = get_settings()

    client = await get_temporal_client()

    logger.info("Starting pricedx deprovisioning worker...")

    worker: Worker = Worker(
        client,
        task_queue=config.pricedx.temporal_pricedx_deboarding_task_queue,
        workflows=[PricedxDeProvisioningWorkflow],
        activities=PricedxDeProvisioningWorkflow.get_activities(),
        debug_mode=True,
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(pricedx_deprovisioning_worker())
