import asyncio

from loguru import logger
import typer
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner, SandboxRestrictions

from app.cli.temporal.core.connection import get_temporal_client
from app.cli.temporal.main import WORKFLOW_MAPPER
from app.core.cli_settings import WorkerConfig, get_workers_config


async def run_workers(worker_process: str) -> None:
    """
    Run workers for the specified queues and workflows
    """
    client = await get_temporal_client()
    workers = []
    if worker_process not in get_workers_config().keys():
        msg = f"Invalid worker process {worker_process}"
        raise ValueError(msg)

    worker_config: WorkerConfig = get_workers_config()[worker_process]
    for queue, workflows in worker_config.workers.items():
        workflow_objs = []
        activities = set()
        for workflow in workflows:
            workflow_obj = WORKFLOW_MAPPER[workflow.__name__]
            workflow_objs.append(workflow_obj)
            activities.update(workflow_obj.get_activities())

        workers.append(
            Worker(
                client,
                workflow_runner=SandboxedWorkflowRunner(
                    restrictions=SandboxRestrictions.default.with_passthrough_modules("app", "loguru"),
                ),
                task_queue=queue,
                workflows=workflow_objs,
                workflow_failure_exception_types=[Exception],
                activities=list(activities),
                debug_mode=True,
            ),
        )
    logger.info(f"Running workers for {worker_process}")
    await asyncio.gather(*[worker.run() for worker in workers])


typer_app = typer.Typer()


@typer_app.command()
def main(process: str = typer.Option(..., help="Queue for the worker")) -> None:
    """
    Run workers for the specified queues and workflows
    """
    asyncio.run(run_workers(worker_process=process))


if __name__ == "__main__":
    typer_app()
