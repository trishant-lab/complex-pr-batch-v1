"""
Workflow helper functions go here. e.g.: Trigger workflow, register namespace etc.
"""
from loguru import logger
from temporalio.client import Client

from app.core.settings import AppSettings, get_settings

from .postgresdatabasesetupworkflow import PostgresDatabaseSetupWorkflow, PostgresDatabaseSetupWorkflowInput


async def trigger_postgres_database_setup_workflow(payload: dict, workflow_id: str):
    """

    :param payload:
    :param workflow_id:
    :return:
    """
    config: AppSettings = get_settings()
    client = await Client.connect(config.temporal_dsn, namespace=config.temporal_namespace)
    result = await client.start_workflow(
        PostgresDatabaseSetupWorkflow.run,
        PostgresDatabaseSetupWorkflowInput(**payload),
        id=workflow_id,
        task_queue=config.temporal_postgres_database_setup_task_queue,
    )
    logger.info(
        f" postgres databsse setup triggered for {payload.get('product')} with run_id: {result}",
    )
    return result.result_run_id
