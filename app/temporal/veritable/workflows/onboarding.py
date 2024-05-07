from collections.abc import Callable
from datetime import timedelta

import pydash
from temporalio import workflow

from app.temporal.core.base import Workflow
from app.temporal.veritable.activities.onboarding import (
    PostgresSetupActivity, NamespaceSetupActivity, ConfigmapSetupActivity, PVCSetupActivity, SecretSetupActivity,
    DnsSetupActivity, UiSetupActivity, KeycloakRealmSetupActivity, ProvisioningJobActivity, KubernetesServiceActivity,
    KubernetesVirtualServiceActivity, DeploymentActivity, VmPodScraperActivity, GrafanaAlertsActivity
)
from app.temporal.veritable.utils.common import VeritableSpec

with workflow.unsafe.imports_passed_through():
    from loguru import logger


@workflow.defn(name="VeritableOnboardingWorkflow")
class VeritableOnboardingWorkflow(Workflow):
    """
    Veritable Onboarding Workflow
    """

    @staticmethod
    def get_activities() -> list[type[Callable]]:
        """
        Return list of activities used in the workflow
        """
        return [
            PostgresSetupActivity.defn, NamespaceSetupActivity.defn, ConfigmapSetupActivity.defn, PVCSetupActivity.defn,
            SecretSetupActivity.defn, DnsSetupActivity.defn, UiSetupActivity.defn, KeycloakRealmSetupActivity.defn,
            ProvisioningJobActivity.defn, KubernetesServiceActivity.defn, KubernetesVirtualServiceActivity.defn,
            DeploymentActivity.defn, VmPodScraperActivity.defn, GrafanaAlertsActivity.defn
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", veritable: VeritableSpec) -> str | None:
        """
        Return unique workflow id from workflow input, guarantees exactly one execution of workflow
        - Add combination of one or more fields from `workflow_input` to uniquely identify workflow
        """
        return veritable.tenant

    @workflow.run
    async def run(self: "Workflow", veritable: VeritableSpec) -> None:
        """
        Entry point for workflow
        """

        # postgres database setup
        await workflow.execute_activity(
            activity=PostgresSetupActivity.defn,
            arg=veritable,
            retry_policy=PostgresSetupActivity.get_retry_policy(),
            start_to_close_timeout=timedelta(seconds=120),
        )

        # create namespace in k8s
        await workflow.execute_activity(
            activity=NamespaceSetupActivity.defn,
            arg=veritable,
            retry_policy=NamespaceSetupActivity.get_retry_policy(),
            start_to_close_timeout=timedelta(seconds=120),
        )

        # create configmap in k8s for namespace
        await workflow.execute_activity(
            activity=ConfigmapSetupActivity.defn,
            arg=veritable,
            retry_policy=ConfigmapSetupActivity.get_retry_policy(),
            start_to_close_timeout=timedelta(seconds=300),
        )

        # create PVC in k8s for namespace
        await workflow.execute_activity(
            activity=PVCSetupActivity.defn,
            arg=veritable,
            retry_policy=PVCSetupActivity.get_retry_policy(),
            start_to_close_timeout=timedelta(seconds=300),
        )

        # create secret in k8s for namespace
        await workflow.execute_activity(
            activity=SecretSetupActivity.defn,
            arg=veritable,
            retry_policy=SecretSetupActivity.get_retry_policy(),
            start_to_close_timeout=timedelta(seconds=300),
        )

        # Create DNS
        await workflow.execute_activity(
            activity=DnsSetupActivity.defn,
            arg=veritable,
            retry_policy=DnsSetupActivity.get_retry_policy(),
            start_to_close_timeout=timedelta(seconds=300),
        )

        # Deploy UI
        await workflow.execute_activity(
            activity=UiSetupActivity.defn,
            arg=veritable,
            retry_policy=UiSetupActivity.get_retry_policy(),
            start_to_close_timeout=timedelta(seconds=300),
        )

        # Create Keycloak realm and users
        await workflow.execute_activity(
            activity=KeycloakRealmSetupActivity.defn,
            arg=veritable,
            retry_policy=KeycloakRealmSetupActivity.get_retry_policy(),
            start_to_close_timeout=timedelta(seconds=300),
        )

        # Provisioning Job
        await workflow.execute_activity(
            activity=ProvisioningJobActivity.defn,
            arg=veritable,
            retry_policy=ProvisioningJobActivity.get_retry_policy(),
            start_to_close_timeout=timedelta(seconds=300),
        )

        # Create Kubernetes Service
        await workflow.execute_activity(
            activity=KubernetesServiceActivity.defn,
            arg=veritable,
            retry_policy=KubernetesServiceActivity.get_retry_policy(),
            start_to_close_timeout=timedelta(seconds=300),
        )

        # Create Kubernetes Virtual Service
        await workflow.execute_activity(
            activity=KubernetesVirtualServiceActivity.defn,
            arg=veritable,
            retry_policy=KubernetesVirtualServiceActivity.get_retry_policy(),
            start_to_close_timeout=timedelta(seconds=300),
        )

        # Deploy server and cli
        await workflow.execute_activity(
            activity=DeploymentActivity.defn,
            arg=veritable,
            retry_policy=DeploymentActivity.get_retry_policy(),
            start_to_close_timeout=timedelta(seconds=300),
        )

        # Scrape VM pods
        await workflow.execute_activity(
            activity=VmPodScraperActivity.defn,
            arg=veritable,
            retry_policy=VmPodScraperActivity.get_retry_policy(),
            start_to_close_timeout=timedelta(seconds=300),
        )

        # Grafana Alerts
        await workflow.execute_activity(
            activity=GrafanaAlertsActivity.defn,
            arg=veritable,
            retry_policy=GrafanaAlertsActivity.get_retry_policy(),
            start_to_close_timeout=timedelta(seconds=300),
        )

        logger.info(f"Veritable onboarding workflow completed for {pydash.get(veritable, 'tenant')}")
        return
