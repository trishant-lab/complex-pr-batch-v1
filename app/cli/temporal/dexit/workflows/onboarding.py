from collections.abc import Callable
from datetime import timedelta

import pydash
from temporalio import workflow

from app.cli.temporal.dexit.models.dexitSpec import DexitSpec
from app.cli.temporal.core.base import Workflow
from app.cli.temporal.dexit.activities.onboarding import (
    PostgresDicomSetupActivity,
    PostgresSetupActivity,
    NamespaceSetupActivity,
    ConfigmapSetupActivity,
    SecretSetupActivity,
    DnsSetupActivity,
    UiSetupActivity,
    KeycloakRealmSetupActivity,
    NovuSetupActivity,
    ProvisioningJobActivity,
    KubernetesServiceActivity,
    KubernetesVirtualServiceActivity,
    StatefulSetPodCreationActivity,
    VmPodScraperActivity,
    GrafanaAlertsActivity,
    TemporalNamespaceCreationActivity,
    FaxSetupActivity,
    HFInferenceEndpointSetupActivity,
    UpdateTenantStatusActivity,
    TenantStatus,
    SendMailActivity,
)


@workflow.defn
class DexitOnboardingWorkflow(Workflow):
    """
    Dexit Onboarding Workflow
    """

    def __init__(self: "Workflow") -> None:
        self.approved: bool = False
        self.deny: bool = False

    @staticmethod
    def get_activities() -> list[type[Callable]]:
        """
        Return list of activities used in the workflow
        """
        return [
            PostgresDicomSetupActivity.defn,
            PostgresSetupActivity.defn,
            NamespaceSetupActivity.defn,
            ConfigmapSetupActivity.defn,
            SecretSetupActivity.defn,
            DnsSetupActivity.defn,
            UiSetupActivity.defn,
            KeycloakRealmSetupActivity.defn,
            NovuSetupActivity.defn,
            ProvisioningJobActivity.defn,
            KubernetesServiceActivity.defn,
            KubernetesVirtualServiceActivity.defn,
            StatefulSetPodCreationActivity.defn,
            VmPodScraperActivity.defn,
            GrafanaAlertsActivity.defn,
            UpdateTenantStatusActivity.defn,
            TemporalNamespaceCreationActivity.defn,
            FaxSetupActivity.defn,
            HFInferenceEndpointSetupActivity.defn,
            SendMailActivity.defn,
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
            await workflow.wait_condition(lambda: self.approved or self.deny)

            if self.deny:
                await workflow.execute_activity(
                    activity=UpdateTenantStatusActivity.defn,
                    arg=TenantStatus(
                        tenant_name=pydash.get(dexit, "tenant"),
                        status="Declined",
                        error_msg="Request Declined",
                    ),
                    retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
                    start_to_close_timeout=timedelta(seconds=120),
                )
                return

            # namespace setup
            await workflow.execute_activity(
                activity=NamespaceSetupActivity.defn,
                arg=dexit,
                retry_policy=NamespaceSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # postgres dicom setup
            await workflow.execute_activity(
                activity=PostgresDicomSetupActivity.defn,
                arg=dexit,
                retry_policy=PostgresDicomSetupActivity.get_retry_policy(),
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

            # fax setup
            await workflow.execute_activity(
                activity=FaxSetupActivity.defn,
                arg=dexit,
                retry_policy=FaxSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # keycloak realm setup
            await workflow.execute_activity(
                activity=KeycloakRealmSetupActivity.defn,
                arg=dexit,
                retry_policy=KeycloakRealmSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # Creating HF Inference Endpoints
            await workflow.execute_activity(
                activity=HFInferenceEndpointSetupActivity.defn,
                arg=dexit,
                retry_policy=HFInferenceEndpointSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(minutes=30),
            )

            # configmap setup
            await workflow.execute_activity(
                activity=ConfigmapSetupActivity.defn,
                arg=dexit,
                retry_policy=ConfigmapSetupActivity.get_retry_policy(),
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
                start_to_close_timeout=timedelta(seconds=600),
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
                activity=StatefulSetPodCreationActivity.defn,
                arg=dexit,
                retry_policy=StatefulSetPodCreationActivity.get_retry_policy(),
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
                arg=TenantStatus(tenant_name=pydash.get(dexit, "tenant"), status="Completed"),
                retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # Send mail to customer
            await workflow.execute_activity(
                activity=SendMailActivity.defn,
                arg=dexit,
                retry_policy=SendMailActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

        except Exception as e:
            workflow.logger.error(f"Error in onboarding workflow: {e}")
            await workflow.execute_activity(
                activity=UpdateTenantStatusActivity.defn,
                arg=TenantStatus(
                    tenant_name=pydash.get(dexit, "tenant"),
                    status="Failed",
                    error_msg=str(e),
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

    @workflow.signal
    async def deny(self: "Workflow") -> None:
        """
        Signal to reject the workflow
        """
        self.deny = True
