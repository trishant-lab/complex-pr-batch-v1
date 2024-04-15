from loguru import logger
from temporalio.client import Client
from temporalio.worker import Worker

from app.temporalworkflows.jeeves.activities import DSLActivities
from app.temporalworkflows.jeeves.workflow import DSLWorkflow
from app.core.settings import AppSettings, get_settings


async def veritable_onboarding_worker():

    config: AppSettings = get_settings()

    client = await Client.connect(config.temporal_dsn, namespace=config.temporal_namespace)
    logger.info("Starting worker for Veritable Onboarding")
    activities = DSLActivities()
    worker: Worker = Worker(
        client,
        task_queue="dsl-task-queue",
        activities=[
            activities.postgres_setup_activity,
            activities.keycloak_setup_activity,
        ],
        workflows=[DSLWorkflow],
        debug_mode=True,
    )

    await worker.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(veritable_onboarding_worker())