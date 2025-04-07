from loguru import logger
from temporalio.client import (
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleSpec,
    ScheduleUpdate,
    ScheduleUpdateInput,
    WorkflowHandle,
)
from temporalio.service import RPCError

from app.cli.temporal.core.base import LaunchpadCLIBaseModel, ScheduleWorkflow, Workflow
from app.cli.temporal.core.connection import get_temporal_client
from app.core.cli_settings import WorkerQueues


async def trigger_workflow(
    workflow_input: LaunchpadCLIBaseModel, workflow: type[Workflow], queue: WorkerQueues
) -> None:
    """
    Run the workflow with the specified input
    """
    client = await get_temporal_client()
    await client.start_workflow(
        workflow=workflow.__name__,
        arg=workflow_input,
        id=workflow.get_workflow_id(workflow_input),
        task_queue=queue.value,
    )
    logger.info(f"Workflow {workflow.__name__} triggered successfully")


async def get_workflow_handle(workflow_input: LaunchpadCLIBaseModel, workflow: type[Workflow]) -> WorkflowHandle:
    """
    Get the workflow handle
    """
    client = await get_temporal_client()
    return client.get_workflow_handle(workflow.get_workflow_id(workflow_input))


async def schedule_workflow(
    workflow: type[ScheduleWorkflow],
    queue: WorkerQueues,
) -> None:
    """
    Schedule the workflow with the specified input
    """
    client = await get_temporal_client()
    try:
        handle = client.get_schedule_handle(workflow.get_workflow_id())

        async def update_schedule_simple(input_: ScheduleUpdateInput) -> ScheduleUpdate:
            schedule_spec = input_.description.schedule.spec

            if isinstance(schedule_spec, ScheduleSpec):
                schedule_spec = workflow.get_schedule_spec()
                input_.description.schedule.spec = schedule_spec
            return ScheduleUpdate(schedule=input_.description.schedule)

        try:
            await handle.update(update_schedule_simple)
        except RPCError:
            await handle.delete()
            raise

    except RPCError:
        await client.create_schedule(
            id=workflow.get_workflow_id(),
            schedule=Schedule(
                action=ScheduleActionStartWorkflow(
                    workflow.__name__,
                    id=workflow.get_workflow_id(),
                    task_queue=queue,
                ),
                spec=workflow.get_schedule_spec(),
            ),
        )
