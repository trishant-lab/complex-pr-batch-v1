from datetime import timedelta
from collections.abc import Callable

import pydash
from temporalio import workflow

from app.cli.temporal.hdp.models.hdpSpec import HDPSpec
from app.cli.temporal.core.base import Workflow


from app.cli.temporal.hdp.activities.onboarding import (
    PostgresSetupActivity,
    NamespaceSetupActivity,
    RedisSetupActivity,
    KeycloakRealmSetupActivity,
    ConfigmapSetupActivity,
    DnsSetupActivity,
    SecretSetupActivity,
    UiSetupActivity,
    KubernetesServiceActivity,
    KubernetesVirtualServiceActivity,
    StatefulSetPodCreationActivity,
    UpdateTenantStatusActivity,
    TenantStatus,
    SendMailActivity,
    BeforeProvisioningMailActivity,
    PVCSetupActivity,
    KestraStatefulSetPodCreationActivity,
)


@workflow.defn
class HDPOnboardingWorkflow(Workflow):
    """
    HDP Onboarding Workflow
    """

    def __init__(self: "Workflow") -> None:
        self.approved: bool = False
        self.deny: bool = False

    @staticmethod
    def get_activities() -> list[type[Callable]]:  # type: ignore
        """
        Return list of activities used in the workflow
        """
        # TODO: update activities
        return [
            PostgresSetupActivity.defn,
            NamespaceSetupActivity.defn,
            RedisSetupActivity.defn,
            KeycloakRealmSetupActivity.defn,
            ConfigmapSetupActivity.defn,
            DnsSetupActivity.defn,
            SecretSetupActivity.defn,
            UiSetupActivity.defn,
            KubernetesServiceActivity.defn,
            KubernetesVirtualServiceActivity.defn,
            StatefulSetPodCreationActivity.defn,
            UpdateTenantStatusActivity.defn,
            SendMailActivity.defn,
            BeforeProvisioningMailActivity.defn,
            PVCSetupActivity.defn,
            KestraStatefulSetPodCreationActivity.defn,
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", hdp: HDPSpec) -> str:
        """
        Return workflow id
        """
        return f"hdp_onboarding_workflow_{hdp.tenant}"

    @workflow.run
    async def run(self: "Workflow", hdp: HDPSpec) -> None:
        """
        Run workflow
        """
        try:
            if not pydash.get(hdp, "emailSent"):
                await workflow.execute_activity(
                    activity=BeforeProvisioningMailActivity.defn,
                    arg=hdp,
                    retry_policy=BeforeProvisioningMailActivity.get_retry_policy(),
                    start_to_close_timeout=timedelta(seconds=120),
                )

            await workflow.wait_condition(lambda: self.approved or self.deny)

            if self.deny:
                await workflow.execute_activity(
                    activity=UpdateTenantStatusActivity.defn,
                    arg=TenantStatus(
                        tenant_name=pydash.get(hdp, "tenant"),
                        status="Declined",
                        error_msg="Request Declined",
                    ),
                    retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
                    start_to_close_timeout=timedelta(seconds=120),
                )
                return

            await workflow.execute_activity(
                activity=PostgresSetupActivity.defn,
                arg=hdp,
                retry_policy=PostgresSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # namespace setup
            await workflow.execute_activity(
                activity=NamespaceSetupActivity.defn,
                arg=hdp,
                retry_policy=NamespaceSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # secret setup
            await workflow.execute_activity(
                activity=SecretSetupActivity.defn,
                arg=hdp,
                retry_policy=SecretSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # statefulset setup
            await workflow.execute_activity(
                activity=RedisSetupActivity.defn,
                arg=hdp,
                retry_policy=RedisSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # configmap setup
            await workflow.execute_activity(
                activity=ConfigmapSetupActivity.defn,
                arg=hdp,
                retry_policy=ConfigmapSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # pvc setup
            await workflow.execute_activity(
                activity=PVCSetupActivity.defn,
                arg=hdp,
                retry_policy=PVCSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # dns setup
            await workflow.execute_activity(
                activity=DnsSetupActivity.defn,
                arg=hdp,
                retry_policy=DnsSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=600),
            )

            # ui setup
            await workflow.execute_activity(
                activity=UiSetupActivity.defn,
                arg=hdp,
                retry_policy=UiSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # keycloak realm setup
            await workflow.execute_activity(
                activity=KeycloakRealmSetupActivity.defn,
                arg=hdp,
                retry_policy=KeycloakRealmSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # Kubernetes Service
            await workflow.execute_activity(
                activity=KubernetesServiceActivity.defn,
                arg=hdp,
                retry_policy=KubernetesServiceActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # Kubernetes Virtual Service
            await workflow.execute_activity(
                activity=KubernetesVirtualServiceActivity.defn,
                arg=hdp,
                retry_policy=KubernetesVirtualServiceActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            await workflow.execute_activity(
                activity=StatefulSetPodCreationActivity.defn,
                arg=hdp,
                retry_policy=StatefulSetPodCreationActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # kestra statefulset setup
            await workflow.execute_activity(
                activity=KestraStatefulSetPodCreationActivity.defn,
                arg=hdp,
                retry_policy=KestraStatefulSetPodCreationActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # Update Tenant Status
            await workflow.execute_activity(
                activity=UpdateTenantStatusActivity.defn,
                arg=TenantStatus(tenant_name=pydash.get(hdp, "tenant"), status="Completed"),
                retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # Send Mail
            await workflow.execute_activity(
                activity=SendMailActivity.defn,
                arg=hdp,
                retry_policy=SendMailActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )

        except Exception as e:
            workflow.logger.error(f"Error in onboarding workflow: {e}")
            await workflow.execute_activity(
                activity=UpdateTenantStatusActivity.defn,
                arg=TenantStatus(
                    tenant_name=pydash.get(hdp, "tenant"),
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
