import asyncio

from loguru import logger
from temporalio.worker import Worker
from temporalio.client import Client

from app.core.settings import AppSettings, get_settings
from app.temporalworkflows.veritable.onboarding.onboardingworkflow import OnboardingWorkflow
from app.temporalworkflows.veritable.onboarding.onboardingactivity import (
    postgres_database_setup_activity, create_namespace_activity, create_configmap_activity, create_pvc_activity,
    secret_setup_activity, create_dns_activity, create_deployment_activity, deploy_veritable_ui_activity,
    create_realm_activity, provisioning_job_activity, create_k8s_service_activity, create_virtual_service_activity,
    create_grafana_alerts_activity, vm_pod_scraper_activity
)


async def veritable_onboarding_worker():
    """
    Workflow worker for veritable onboarding
    """
    config: AppSettings = get_settings()

    client = await Client.connect(config.temporal_dsn, namespace=config.temporal_namespace)

    logger.info("Starting veritable onboarding worker...")

    worker: Worker = Worker(
        client,
        task_queue=config.temporal_veritable_onboarding_task_queue,
        workflows=[OnboardingWorkflow],
        activities=[
            postgres_database_setup_activity,
            create_namespace_activity,
            create_configmap_activity,
            create_pvc_activity,
            secret_setup_activity,
            create_dns_activity,
            create_deployment_activity,
            deploy_veritable_ui_activity,
            create_realm_activity,
            provisioning_job_activity,
            create_k8s_service_activity,
            create_virtual_service_activity,
            vm_pod_scraper_activity,
            create_grafana_alerts_activity
        ],
        debug_mode=True
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(veritable_onboarding_worker())
