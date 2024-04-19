import asyncio

from loguru import logger
from temporalio.worker import Worker
from temporalio.client import Client

from app.core.settings import AppSettings, get_settings
from app.temporalworkflows.veritable.deprovisioning.deprovisioning_activity import delete_all_resources
from app.temporalworkflows.veritable.deprovisioning.deprovisioning_workflow import DeprovisioningWorkflow


async def veritable_de_provisioning_worker():
    """
    Workflow worker for veritable deprovisioning
    """
    config: AppSettings = get_settings()

    client = await Client.connect(config.temporal_dsn, namespace=config.temporal_namespace)

    logger.info("Starting veritable deprovisioning worker...")

    worker: Worker = Worker(
        client,
        task_queue=config.temporal_veritable_deprovisioning_task_queue,
        workflows=[DeprovisioningWorkflow],
        activities=[delete_all_resources],
        debug_mode=True
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(veritable_de_provisioning_worker())
