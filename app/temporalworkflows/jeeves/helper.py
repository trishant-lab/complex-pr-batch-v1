import uuid

import dacite
import yaml
from loguru import logger
from temporalio.client import Client

from app.core.settings import AppSettings, get_settings
from app.temporalworkflows.jeeves.workflow import DSLInput, DSLWorkflow


async def trigger_dsl_workflow(dsl_yaml: str) -> None:

    config: AppSettings = get_settings()

    logger.info("Starting DSL workflow")
    dsl_input = dacite.from_dict(DSLInput, yaml.safe_load(dsl_yaml))

    client = await Client.connect(config.temporal_dsn, namespace=config.temporal_namespace)
    result = await client.start_workflow(
        DSLWorkflow.run,
        dsl_input,
        id=f"dsl-workflow-id-{uuid.uuid4()}",
        task_queue="dsl-task-queue",
    )
    logger.info(
        f" DSL workflow triggered with run_id: {result.run_id}",
    )
