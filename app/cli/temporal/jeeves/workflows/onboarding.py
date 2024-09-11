from datetime import timedelta
from collections.abc import Callable

import pydash
from temporalio import workflow

from app.cli.jeeves.jeeves import JeevesSpec
from app.cli.temporal.core.base import Workflow

from app.cli.temporal.jeeves.activities.onboarding import (
    PostgresSetupActivity,
    NamespaceSetupActivity,
    ConfigmapSetupActivity,
    PVCSetupActivity,
    SecretSetupActivity,
    StateFullSetSetupActivity,
    DnsSetupActivity,
    UiSetupActivity,
    KeycloakRealmSetupActivity,
    NovuSetupActivity,
    ChatwootSetupActivity,
    ProvisioningJobActivity,
    KubernetesServiceActivity,
    KubernetesVirtualServiceActivity,
    DeploymentActivity,
    VmPodScraperActivity,
    AiVoiceSetupActivity,
    TemporalNamespaceCreationActivity,
    SendMailActivity,
    UpdateTenantStatusActivity,
    TenantStatus,
    BeforeProvisioningMailActivity,
    PreLoadAssetsJobActivity,
)


@workflow.defn
class JeevesOnboardingWorkflow(Workflow):
    """
    Jeeves Onboarding Workflow
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
            PostgresSetupActivity.defn,
            NamespaceSetupActivity.defn,
            ConfigmapSetupActivity.defn,
            PVCSetupActivity.defn,
            SecretSetupActivity.defn,
            StateFullSetSetupActivity.defn,
            DnsSetupActivity.defn,
            UiSetupActivity.defn,
            KeycloakRealmSetupActivity.defn,
            NovuSetupActivity.defn,
            ChatwootSetupActivity.defn,
            ProvisioningJobActivity.defn,
            KubernetesServiceActivity.defn,
            KubernetesVirtualServiceActivity.defn,
            DeploymentActivity.defn,
            VmPodScraperActivity.defn,
            AiVoiceSetupActivity.defn,
            SendMailActivity.defn,
            TemporalNamespaceCreationActivity.defn,
            UpdateTenantStatusActivity.defn,
            BeforeProvisioningMailActivity.defn,
            PreLoadAssetsJobActivity.defn,
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", jeeves: JeevesSpec) -> str:
        """
        Return workflow id
        """
        return f"jeeves_onboarding_workflow_{jeeves.tenant}"

    @workflow.run
    async def run(self: "Workflow", jeeves: JeevesSpec) -> None:
        """
        Run workflow
        """
        try:
            if not pydash.get(jeeves, "emailSent"):
                await workflow.execute_activity(
                    activity=BeforeProvisioningMailActivity.defn,
                    arg=jeeves,
                    retry_policy=BeforeProvisioningMailActivity.get_retry_policy(),
                    start_to_close_timeout=timedelta(seconds=120),
                )

            await workflow.wait_condition(lambda: self.approved or self.deny)

            if self.deny:
                await workflow.execute_activity(
                    activity=UpdateTenantStatusActivity.defn,
                    arg=TenantStatus(
                        tenant_name=pydash.get(jeeves, "tenant"),
                        status="Declined",
                        error_msg="Request Declined",
                    ),
                    retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
                    start_to_close_timeout=timedelta(seconds=120),
                )
                return

            await workflow.execute_activity(
                activity=PostgresSetupActivity.defn,
                arg=jeeves,
                retry_policy=PostgresSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # namespace setup
            await workflow.execute_activity(
                activity=NamespaceSetupActivity.defn,
                arg=jeeves,
                retry_policy=NamespaceSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # secret setup
            await workflow.execute_activity(
                activity=SecretSetupActivity.defn,
                arg=jeeves,
                retry_policy=SecretSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # chatwoot setup
            await workflow.execute_activity(
                activity=ChatwootSetupActivity.defn,
                arg=jeeves,
                retry_policy=ChatwootSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # novu setup
            await workflow.execute_activity(
                activity=NovuSetupActivity.defn,
                arg=jeeves,
                retry_policy=NovuSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # statefulset setup
            await workflow.execute_activity(
                activity=StateFullSetSetupActivity.defn,
                arg=jeeves,
                retry_policy=StateFullSetSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # configmap setup
            await workflow.execute_activity(
                activity=ConfigmapSetupActivity.defn,
                arg=jeeves,
                retry_policy=ConfigmapSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # pvc setup
            await workflow.execute_activity(
                activity=PVCSetupActivity.defn,
                arg=jeeves,
                retry_policy=PVCSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # dns setup
            await workflow.execute_activity(
                activity=DnsSetupActivity.defn,
                arg=jeeves,
                retry_policy=DnsSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=600),
            )

            # ui setup
            await workflow.execute_activity(
                activity=UiSetupActivity.defn,
                arg=jeeves,
                retry_policy=UiSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # keycloak realm setup
            await workflow.execute_activity(
                activity=KeycloakRealmSetupActivity.defn,
                arg=jeeves,
                retry_policy=KeycloakRealmSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # Provisioning Job
            await workflow.execute_activity(
                activity=ProvisioningJobActivity.defn,
                arg=jeeves,
                retry_policy=ProvisioningJobActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # Kubernetes Service
            await workflow.execute_activity(
                activity=KubernetesServiceActivity.defn,
                arg=jeeves,
                retry_policy=KubernetesServiceActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # Kubernetes Virtual Service
            await workflow.execute_activity(
                activity=KubernetesVirtualServiceActivity.defn,
                arg=jeeves,
                retry_policy=KubernetesVirtualServiceActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # Deploy server and cli
            await workflow.execute_activity(
                activity=DeploymentActivity.defn,
                arg=jeeves,
                retry_policy=DeploymentActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # Vm Pod Scraper
            await workflow.execute_activity(
                activity=VmPodScraperActivity.defn,
                arg=jeeves,
                retry_policy=VmPodScraperActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # Temporal Namespace Creation
            await workflow.execute_activity(
                activity=TemporalNamespaceCreationActivity.defn,
                arg=jeeves,
                retry_policy=TemporalNamespaceCreationActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # Ai Voice Setup
            await workflow.execute_activity(
                activity=AiVoiceSetupActivity.defn,
                arg=jeeves,
                retry_policy=AiVoiceSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=300),
            )

            # PreLoadAssetsJob
            await workflow.execute_activity(
                activity=PreLoadAssetsJobActivity.defn,
                arg=jeeves,
                retry_policy=PreLoadAssetsJobActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=400),
            )

            # Update Tenant Status
            await workflow.execute_activity(
                activity=UpdateTenantStatusActivity.defn,
                arg=TenantStatus(tenant_name=pydash.get(jeeves, "tenant"), status="Completed"),
                retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # Send Mail
            await workflow.execute_activity(
                activity=SendMailActivity.defn,
                arg=jeeves,
                retry_policy=SendMailActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

        except Exception as e:
            workflow.logger.error(f"Error in onboarding workflow: {e}")
            await workflow.execute_activity(
                activity=UpdateTenantStatusActivity.defn,
                arg=TenantStatus(
                    tenant_name=pydash.get(jeeves, "tenant"),
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
