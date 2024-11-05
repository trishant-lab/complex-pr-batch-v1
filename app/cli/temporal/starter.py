from loguru import logger
from temporalio.client import WorkflowHandle

from app.cli.temporal.core.base import LaunchpadCLIBaseModel, Workflow
from app.cli.temporal.core.connection import get_temporal_client


async def trigger_workflow(workflow_input: LaunchpadCLIBaseModel, workflow: type[Workflow], queue: str) -> None:
    """
    Run the workflow with the specified input
    """
    client = await get_temporal_client()
    await client.start_workflow(
        workflow=workflow.__name__,
        arg=workflow_input,
        id=workflow.get_workflow_id(workflow_input),
        task_queue=queue,
    )
    logger.info(f"Workflow {workflow.__name__} triggered successfully")


async def get_workflow_handle(workflow_input: LaunchpadCLIBaseModel, workflow: type[Workflow]) -> WorkflowHandle:
    """
    Get the workflow handle
    """
    client = await get_temporal_client()
    return client.get_workflow_handle(workflow.get_workflow_id(workflow_input))
