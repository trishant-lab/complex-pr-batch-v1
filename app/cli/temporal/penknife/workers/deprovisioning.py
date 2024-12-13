import asyncio
from app.cli.temporal.penknife.workflows.deprovisioning import PenknifeDeProvisioningWorkflow
from app.core.settings import AppSettings, get_settings
from loguru import logger
from temporalio.worker import Worker
from temporalio.client import Client


async def penknife_deprovisioning_worker() -> None:
    """
    Workflow worker for penknife onboarding
    """
    config: AppSettings = get_settings()

    client = await Client.connect(config.temporal.dsn, namespace=config.temporal.namespace)

    logger.info("Starting penknife de-provisioning worker...")

    worker: Worker = Worker(
        client,
        task_queue=config.penknife.temporal_penknife_deboarding_task_queue,
        workflows=[PenknifeDeProvisioningWorkflow],
        activities=PenknifeDeProvisioningWorkflow.get_activities(),
        debug_mode=True,
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(penknife_deprovisioning_worker())
