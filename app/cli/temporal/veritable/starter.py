from loguru import logger
from temporalio.client import Client

from app.cli.temporal.veritable.workflows.deprovisioning import (
    VeritableDeProvisioningWorkflow
)
from app.cli.temporal.veritable.workflows.onboarding import VeritableOnboardingWorkflow
from app.cli.temporal.veritable.workflows.postgres import VeritablePostgresSetupWorkflow
from app.cli.veritable.common import VeritableSpec
from app.core.settings import AppSettings, get_settings


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
        task_queue=config.veritable.temporal_veritable_onboarding_task_queue,
    )
    logger.info(f"Veritable onboarding workflow triggered for tenant {payload['tenant']}")


async def trigger_veritable_postgres_setup_workflow(payload: dict) -> None:
    """
    Trigger the veritable postgres setup workflow
    :param payload:
    :return:
    """
    config: AppSettings = get_settings()
    client = await Client.connect(config.temporal.dsn, namespace=config.temporal.namespace)

    await client.start_workflow(
        VeritablePostgresSetupWorkflow.__name__,
        VeritableSpec(**payload),
        id=VeritablePostgresSetupWorkflow.get_workflow_id(veritable=VeritableSpec(**payload)),
        task_queue=config.veritable.temporal_veritable_postgres_setup_task_queue,
    )
    logger.info(f"Veritable postgres setup workflow triggered for tenant {payload['tenant']}")


async def trigger_veritable_de_provisioning_workflow(tenant_name: str) -> None:
    """
    Trigger the veritable deprovisioning workflow
    """
    config: AppSettings = get_settings()
    client = await Client.connect(config.temporal.dsn, namespace=config.temporal.namespace)

    await client.start_workflow(
        VeritableDeProvisioningWorkflow.__name__,
        VeritableSpec(tenant=tenant_name),
        id=VeritableDeProvisioningWorkflow.get_workflow_id(
            workflow_input=VeritableSpec(tenant=tenant_name)
        ),
        task_queue=config.veritable.temporal_veritable_deboarding_task_queue,
    )
    logger.info(f"Veritable deprovisioning workflow triggered for tenant {tenant_name}")
