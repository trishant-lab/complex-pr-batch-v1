from datetime import timedelta
from typing import Callable

import pydash
from temporalio import workflow

from app.cli.dexit.models.dexitSpec import DexitSpec
from app.cli.temporal.core.base import Workflow

from app.cli.temporal.dexit.activities.onboarding import (
    PostgresSetupActivity, NamespaceSetupActivity, ConfigmapSetupActivity, PVCSetupActivity, SecretSetupActivity,
    DnsSetupActivity, UiSetupActivity, KeycloakRealmSetupActivity, NovuSetupActivity,
    ProvisioningJobActivity, KubernetesServiceActivity, KubernetesVirtualServiceActivity,
    DeploymentActivity, VmPodScraperActivity, GrafanaAlertsActivity,
    TemporalNamespaceCreationActivity
)
from app.cli.temporal.veritable.activities.onboarding import UpdateTenantStatusActivity, TenantStatus


@workflow.defn
class DexitOnboardingWorkflow(Workflow):
    """
    Dexit Onboarding Workflow
    """
    approved: bool = False

    @staticmethod
    def get_activities() -> list[type[Callable]]:
        """
        Return list of activities used in the workflow
        """
        return [
            PostgresSetupActivity.defn, NamespaceSetupActivity.defn, ConfigmapSetupActivity.defn, PVCSetupActivity.defn,
            SecretSetupActivity.defn, DnsSetupActivity.defn, UiSetupActivity.defn,
            KeycloakRealmSetupActivity.defn, NovuSetupActivity.defn,
            ProvisioningJobActivity.defn, KubernetesServiceActivity.defn, KubernetesVirtualServiceActivity.defn,
            DeploymentActivity.defn, VmPodScraperActivity.defn, GrafanaAlertsActivity.defn,
            UpdateTenantStatusActivity.defn, TemporalNamespaceCreationActivity.defn
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", dexit: DexitSpec) -> str:
        """
        Return workflow id
        """
        return f"dexit_onboarding_workflow_{dexit.tenant}"

    @workflow.run
    async def run(self: "Workflow", dexit: DexitSpec) -> None:
        """
        Run workflow
        """
        try:
            await workflow.wait_condition(lambda: self.approved)

            # namespace setup
            await workflow.execute_activity(
                activity=NamespaceSetupActivity.defn,
                arg=dexit,
                retry_policy=NamespaceSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # postgres setup
            await workflow.execute_activity(
                activity=PostgresSetupActivity.defn,
                arg=dexit,
                retry_policy=PostgresSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # secret setup
            await workflow.execute_activity(
                activity=SecretSetupActivity.defn,
                arg=dexit,
                retry_policy=SecretSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # novu setup
            await workflow.execute_activity(
                activity=NovuSetupActivity.defn,
                arg=dexit,
                retry_policy=NovuSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # configmap setup
            await workflow.execute_activity(
                activity=ConfigmapSetupActivity.defn,
                arg=dexit,
                retry_policy=ConfigmapSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # pvc setup
            await workflow.execute_activity(
                activity=PVCSetupActivity.defn,
                arg=dexit,
                retry_policy=PVCSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # dns setup
            await workflow.execute_activity(
                activity=DnsSetupActivity.defn,
                arg=dexit,
                retry_policy=DnsSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=600),
            )

            # ui setup
            await workflow.execute_activity(
                activity=UiSetupActivity.defn,
                arg=dexit,
                retry_policy=UiSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # keycloak realm setup
            await workflow.execute_activity(
                activity=KeycloakRealmSetupActivity.defn,
                arg=dexit,
                retry_policy=KeycloakRealmSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # Provisioning Job
            await workflow.execute_activity(
                activity=ProvisioningJobActivity.defn,
                arg=dexit,
                retry_policy=ProvisioningJobActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # Kubernetes Service
            await workflow.execute_activity(
                activity=KubernetesServiceActivity.defn,
                arg=dexit,
                retry_policy=KubernetesServiceActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # Kubernetes Virtual Service
            await workflow.execute_activity(
                activity=KubernetesVirtualServiceActivity.defn,
                arg=dexit,
                retry_policy=KubernetesVirtualServiceActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # Deploy server and cli
            await workflow.execute_activity(
                activity=DeploymentActivity.defn,
                arg=dexit,
                retry_policy=DeploymentActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # Vm Pod Scraper
            await workflow.execute_activity(
                activity=VmPodScraperActivity.defn,
                arg=dexit,
                retry_policy=VmPodScraperActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # Grafana Alerts
            await workflow.execute_activity(
                activity=GrafanaAlertsActivity.defn,
                arg=dexit,
                retry_policy=GrafanaAlertsActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # Temporal Namespace Creation
            await workflow.execute_activity(
                activity=TemporalNamespaceCreationActivity.defn,
                arg=dexit,
                retry_policy=TemporalNamespaceCreationActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # Update Tenant Status
            await workflow.execute_activity(
                activity=UpdateTenantStatusActivity.defn,
                arg=TenantStatus(
                    tenant_name=pydash.get(dexit, 'tenant'),
                    status="completed"
                ),
                retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )
        except Exception as e:
            workflow.logger.error(f"Error in onboarding workflow: {e}")
            await workflow.execute_activity(
                activity=UpdateTenantStatusActivity.defn,
                arg=TenantStatus(
                    tenant_name=pydash.get(dexit, 'tenant'),
                    status="Failed",
                    error_msg=str(e)
                ),
                retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )
            raise e

    @workflow.signal
    async def approve(self: "Workflow") -> None:
        """
        Signal to approve the workflow
        """
        self.approved = True
