from loguru import logger
from temporalio.client import Client

from app.core.settings import AppSettings, get_settings
from app.temporal.veritable.workflows.onboarding import VeritableOnboardingWorkflow
from app.temporal.veritable.utils.common import VeritableSpec


async def trigger_veritable_onboarding_workflow(payload: dict) -> None:
    """
    Trigger the veritable onboarding workflow
    :param payload:
    :return:
    """
    config: AppSettings = get_settings()
    client = await Client.connect(config.temporal.dsn, namespace=config.temporal.namespace)

    await client.start_workflow(
        VeritableOnboardingWorkflow.__name__,
        VeritableSpec(**payload),
        id=VeritableOnboardingWorkflow.get_workflow_id(veritable=VeritableSpec(**payload)),
        task_queue=config.temporal_veritable_onboarding_task_queue,
    )
    logger.info(f"Veritable onboarding workflow triggered for tenant {payload['tenant']}")
