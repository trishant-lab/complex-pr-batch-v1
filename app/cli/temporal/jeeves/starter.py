from loguru import logger
from temporalio.client import Client

from app.cli.temporal.jeeves.workflows.onboarding import JeevesOnboardingWorkflow
from app.cli.jeeves.common import JeevesSpec
from app.core.settings import AppSettings, get_settings


async def trigger_jeeves_onboarding_workflow(payload: dict) -> None:
    """
    Trigger the jeeves onboarding workflow
    :param payload:
    :return:
    """
    config: AppSettings = get_settings()
    client = await Client.connect(config.temporal.dsn, namespace=config.temporal.namespace)

    await client.start_workflow(
        JeevesOnboardingWorkflow.__name__,
        JeevesSpec(**payload),
        id=JeevesOnboardingWorkflow.get_workflow_id(jeeves=JeevesSpec(**payload)),
        task_queue=config.jeeves.temporal_jeeves_onboarding_task_queue,
    )
    logger.info(f"Jeeves onboarding workflow triggered for tenant {payload['tenant']}")


