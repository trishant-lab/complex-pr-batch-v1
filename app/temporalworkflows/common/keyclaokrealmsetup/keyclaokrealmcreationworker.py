from loguru import logger
from temporalio.client import Client
from temporalio.worker import Worker

from app.core.settings import AppSettings, get_settings
from app.temporalworkflows.commonworkflows.keyclaokrealmsetup.keyclaokrealmcreationworkflow import (
    KeyclaokRealmCreationWorkflow,
)
from app.temporalworkflows.commonworkflows.keyclaokrealmsetup.keyclaokrealmcreationactivity import (
    create_keycloak_realm_activity,
)

config: AppSettings = get_settings()


async def keycloak_realm_creation_worker() -> None:
    """
    Workflow worker for keycloak realm creation
    :return:
    :rtype:
    """
    client = await Client.connect(config.temporal_dsn, namespace=config.temporal_namespace)
    logger.info("Starting keycloak realm creation worker...")
    worker: Worker = Worker(
        client,
        task_queue=config.temporal_keycloak_realm_creation_task_queue,
        workflows=[KeyclaokRealmCreationWorkflow],
        activities=[create_keycloak_realm_activity],
        debug_mode=True,
    )
    await worker.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(keycloak_realm_creation_worker())
