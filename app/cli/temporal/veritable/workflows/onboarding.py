from collections.abc import Callable
from datetime import timedelta

import pydash
from temporalio import workflow

from app.cli.temporal.core.base import Workflow
from app.cli.temporal.veritable.activities.onboarding import (
    PostgresSetupActivity, NamespaceSetupActivity, ConfigmapSetupActivity, PVCSetupActivity, SecretSetupActivity,
    DnsSetupActivity, UiSetupActivity, KeycloakRealmSetupActivity, ProvisioningJobActivity, KubernetesServiceActivity,
    KubernetesVirtualServiceActivity, DeploymentActivity, VmPodScraperActivity, UpdateTenantStatusActivity,
    TenantStatus, FernetKeyGenerationActivity
)
from app.cli.veritable.models.veritableSpec import VeritableSpec
from app.models.tenant import TenantStatusEnum

with workflow.unsafe.imports_passed_through():
    from loguru import logger


@workflow.defn
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
            PostgresSetupActivity.defn, NamespaceSetupActivity.defn, ConfigmapSetupActivity.defn,
            PVCSetupActivity.defn, SecretSetupActivity.defn, DnsSetupActivity.defn, UiSetupActivity.defn,
            KeycloakRealmSetupActivity.defn, ProvisioningJobActivity.defn, KubernetesServiceActivity.defn,
            KubernetesVirtualServiceActivity.defn, DeploymentActivity.defn, VmPodScraperActivity.defn,
            UpdateTenantStatusActivity.defn, FernetKeyGenerationActivity.defn
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", veritable: VeritableSpec) -> str | None:
        """
        Return unique workflow id from workflow input, guarantees exactly one execution of workflow
        - Add combination of one or more fields from `workflow_input` to uniquely identify workflow
        """
        return f"veritable_onboarding_workflow_{veritable.tenant}"

    @workflow.run
    async def run(self: "Workflow", veritable: VeritableSpec) -> None:
        """
        Entry point for workflow
        """

        # todo vaildate customer id

        # postgres database setup
        try:
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

            # generate fernet key and store in 1Password
            await workflow.execute_activity(
                activity=FernetKeyGenerationActivity.defn,
                arg=veritable,
                retry_policy=FernetKeyGenerationActivity.get_retry_policy(),
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

            await workflow.execute_activity(
                activity=UpdateTenantStatusActivity.defn,
                arg=TenantStatus(
                    tenant_name=pydash.get(veritable, 'tenant'),
                    status=TenantStatusEnum.Completed,
                    error_msg=None
                ),
                retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            logger.info(f"Veritable onboarding workflow completed for {pydash.get(veritable, 'tenant')}")
            return

        except Exception as e:
            logger.error(f"Error in Veritable onboarding workflow: {e}")

            await workflow.execute_activity(
                activity=UpdateTenantStatusActivity.defn,
                arg=TenantStatus(
                    tenant_name=pydash.get(veritable, 'tenant'),
                    status=TenantStatusEnum.Failed,
                    error_msg=str(e)
                ),
                retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            raise e
