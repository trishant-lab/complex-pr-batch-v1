import asyncio

from loguru import logger
from temporalio.worker import Worker
from temporalio.client import Client

from app.core.settings import AppSettings, get_settings
from app.cli.temporal.jeeves.workflows.deprovisioning import JeevesDeProvisioningWorkflow


async def jeeves_deprovisioning_worker() -> None:
    """
    Workflow worker for jeeves onboarding
    """
    config: AppSettings = get_settings()

    client = await Client.connect(config.temporal.dsn, namespace=config.temporal.namespace)

    logger.info("Starting jeeves de-provisioning worker...")

    worker: Worker = Worker(
        client,
        task_queue=config.jeeves.temporal_jeeves_deboarding_task_queue,
        workflows=[JeevesDeProvisioningWorkflow],
        activities=JeevesDeProvisioningWorkflow.get_activities(),
        debug_mode=True,
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(jeeves_deprovisioning_worker())
