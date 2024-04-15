"""
Workflow helper functions go here. e.g.: Trigger workflow, register namespace etc.
"""
from loguru import logger
from temporalio.client import Client

from app.core.settings import AppSettings, get_settings

from .keyclaokrealmcreationworkflow import KeyclaokRealmCreationWorkflow, KeyclaokRealmCreationWorkflowInput


async def trigger_keycloak_realm_creation_workflow(payload: dict, workflow_id: str):
    """

    :param payload:
    :param workflow_id:
    :return:
    """
    config: AppSettings = get_settings()
    client = await Client.connect(config.temporal_dsn, namespace=config.temporal_namespace)
    result = await client.start_workflow(
        KeyclaokRealmCreationWorkflow.run,
        KeyclaokRealmCreationWorkflowInput(**payload),
        id=f"keycloak_realm_creation_workflow_{workflow_id}",
        task_queue=config.temporal_keycloak_realm_creation_task_queue,
    )
    logger.info(
        f" keycloak realm creation setup triggered for {payload.get('product')=} with run_id: {result}",
    )