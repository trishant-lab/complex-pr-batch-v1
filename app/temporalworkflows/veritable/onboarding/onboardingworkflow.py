from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

from loguru import logger

from app.temporalworkflows.veritable.onboarding.onboardingactivity import (
    postgres_database_setup_activity, create_namespace_activity, create_pvc_activity, secret_setup_activity,
    deploy_veritable_ui_activity, create_realm_activity, create_dns_activity, provisioning_job_activity,
    create_k8s_service_activity, create_virtual_service_activity, create_configmap_activity, create_deployment_activity,
    vm_pod_scraper_activity, create_grafana_alerts_activity
)
from app.temporalworkflows.veritable.veritableSpec import VeritableSpec


@workflow.defn(name="onboarding_workflow", sandboxed=False)
class OnboardingWorkflow:
    @workflow.run
    async def run(self, veritable_spec: VeritableSpec) -> None:
        """
        Onboarding workflow
        """
        logger.info(f"Starting Onboarding Workflow for Veritable tenant: {veritable_spec.tenant}")

        retry_policy: RetryPolicy = RetryPolicy(
            backoff_coefficient=2.0,
            maximum_attempts=1,
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=60),
        )

        # postgres database setup
        await workflow.execute_activity(
            postgres_database_setup_activity,
            veritable_spec,
            retry_policy=retry_policy,
            start_to_close_timeout=timedelta(seconds=120),
        )

        # create namespace in k8s
        await workflow.execute_activity(
            create_namespace_activity,
            veritable_spec,
            retry_policy=retry_policy,
            start_to_close_timeout=timedelta(seconds=120),
        )

        # create configmap in k8s for namespace
        await workflow.execute_activity(
            create_configmap_activity,
            veritable_spec,
            retry_policy=retry_policy,
            start_to_close_timeout=timedelta(seconds=300),
        )

        # create PVC in k8s for namespace
        await workflow.execute_activity(
            create_pvc_activity,
            veritable_spec,
            retry_policy=retry_policy,
            start_to_close_timeout=timedelta(seconds=300),
        )

        # create secret in k8s for namespace
        await workflow.execute_activity(
            secret_setup_activity,
            veritable_spec,
            retry_policy=retry_policy,
            start_to_close_timeout=timedelta(seconds=300),
        )

        # Create DNS
        await workflow.execute_activity(
            create_dns_activity,
            veritable_spec,
            retry_policy=retry_policy,
            start_to_close_timeout=timedelta(seconds=300),
        )

        # Deploy ui
        await workflow.execute_activity(
            deploy_veritable_ui_activity,
            veritable_spec,
            retry_policy=retry_policy,
            start_to_close_timeout=timedelta(seconds=300),
        )

        # Create keycloak realm
        await workflow.execute_activity(
            create_realm_activity,
            veritable_spec,
            retry_policy=retry_policy,
            start_to_close_timeout=timedelta(seconds=300),
        )

        # Provisioning job
        await workflow.execute_activity(
            provisioning_job_activity,
            veritable_spec,
            retry_policy=retry_policy,
            start_to_close_timeout=timedelta(seconds=300),
        )

        # Create service in k8s for namespace
        await workflow.execute_activity(
            create_k8s_service_activity,
            veritable_spec,
            retry_policy=retry_policy,
            start_to_close_timeout=timedelta(seconds=300),
        )

        # Create virtual service in k8s for namespace (Istio)
        await workflow.execute_activity(
            create_virtual_service_activity,
            veritable_spec,
            retry_policy=retry_policy,
            start_to_close_timeout=timedelta(seconds=300),
        )

        # Create deployment in k8s for namespace
        await workflow.execute_activity(
            create_deployment_activity,
            veritable_spec,
            retry_policy=retry_policy,
            start_to_close_timeout=timedelta(seconds=300),
        )

        # Create VMPod Scrapper for Grafana metrics
        await workflow.execute_activity(
            vm_pod_scraper_activity,
            veritable_spec,
            retry_policy=retry_policy,
            start_to_close_timeout=timedelta(seconds=300),
        )

        # Create Grafana Alerts
        await workflow.execute_activity(
            create_grafana_alerts_activity,
            veritable_spec,
            retry_policy=retry_policy,
            start_to_close_timeout=timedelta(seconds=300),
        )

        logger.info(f"Finished Onboarding Workflow for Veritable tenant: {veritable_spec.tenant}")

        return
