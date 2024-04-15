"""
Add views workflow workers go here.
"""
import asyncio

from loguru import logger
from temporalio.client import Client
from temporalio.worker import Worker

from app.core.settings import AppSettings, get_settings
from app.temporalworkflows.commonworkflows.postgresdatabasesetup.postgresdatabasesetupworkflow import (
    PostgresDatabaseSetupWorkflow
)
from app.temporalworkflows.commonworkflows.postgresdatabasesetup.postgresdatabasesetupactivity import (
    create_user_activity, generate_random_password, grant_permissions_activity, create_schema_activity
)


async def postgres_database_setup_worker() -> None:
    """
        Workflow worker for add views
    :return:
    """
    config: AppSettings = get_settings()

    client = await Client.connect(config.temporal_dsn, namespace=config.temporal_namespace)
    logger.info("Starting postgres database setup worker...")
    worker: Worker = Worker(
        client,
        task_queue=config.temporal_postgres_database_setup_task_queue,
        workflows=[PostgresDatabaseSetupWorkflow],
        activities=[
            generate_random_password,
            create_user_activity,
            create_schema_activity,
            grant_permissions_activity
        ],
        debug_mode=True,
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(postgres_database_setup_worker())
