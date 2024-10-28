from collections.abc import Callable
from temporalio import workflow
import pydash


from app.cli.temporal.activities.sendMail import (
    SendAfterProvisioningMailActivity,
    SendAfterProvisioningMailActivityModel,
    SendBeforeProvisioningMailActivity,
    SendBeforeProvisioningMailActivityModel,
)

from app.cli.temporal.activities.updateTenantStatus import TenantStatus, UpdateTenantStatusActivity
from app.cli.temporal.core.base import Workflow


from app.cli.temporal.zsegment.models.zsegmentSpec import ZSegmentSpec


with workflow.unsafe.imports_passed_through():
    from app.core.settings import AppSettings, ZSegmentSettings, get_settings


ProductName = "zsegment"
OnePasswordVaultName = "zsegment"


@workflow.defn(name="ZSegmentOnboardingWorkflow", sandboxed=False)
class ZSegmentOnboardingWorkflow(Workflow):
    """
    ZSegment Onboarding Workflow
    """

    def __init__(self: "Workflow") -> None:
        self.approved: bool = False
        self.deny: bool = False

    @staticmethod
    def get_activities() -> list[type[Callable]]:  # type: ignore
        """
        Return list of activities used in the workflow
        """
        return [
            SendBeforeProvisioningMailActivity.defn,
            SendAfterProvisioningMailActivity.defn,
            UpdateTenantStatusActivity.defn,
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", zsegment: ZSegmentSpec) -> str:
        """
        Return workflow id
        """
        return f"zsegment_onboarding_workflow_{pydash.get(zsegment, 'tenant')}"

    @workflow.run
    async def run(self: "Workflow", zsegment: ZSegmentSpec) -> None:
        """
        Run the workflow
        """
        config: AppSettings = get_settings()
        zsegment_config: ZSegmentSettings = config.zsegment

        first_name = pydash.get(zsegment, "firstName")
        last_name = pydash.get(zsegment, "lastName")
        email = pydash.get(zsegment, "email")
        tenant = pydash.get(zsegment, "tenant")
        realm_name = tenant

        try:
            if not pydash.get(zsegment, "emailSent"):
                await workflow.execute_activity(
                    activity=SendBeforeProvisioningMailActivity.defn,
                    arg=SendBeforeProvisioningMailActivityModel(
                        user_details={
                            "firstName": first_name,
                            "lastName": last_name,
                            "email": email,
                        },
                        product=ProductName,
                        from_name=zsegment_config.sender_name,
                        email_from=zsegment_config.sender_email,
                    ),
                    retry_policy=SendBeforeProvisioningMailActivity.get_retry_policy(),
                    start_to_close_timeout=SendBeforeProvisioningMailActivity.get_timeout(),
                )

            # Wait for approval or denial
            await workflow.wait_condition(lambda: self.approved or self.deny)

            # Update tenant status if request is declined
            if self.deny:
                await workflow.execute_activity(
                    activity=UpdateTenantStatusActivity.defn,
                    arg=TenantStatus(
                        tenant_name=tenant,
                        status="Declined",
                        error_msg="Request Declined",
                    ),
                    start_to_close_timeout=UpdateTenantStatusActivity.get_timeout(),
                    retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
                )

            # Todo Add Activties

            # update tenant status
            await workflow.execute_activity(
                activity=UpdateTenantStatusActivity.defn,
                arg=TenantStatus(tenant_name=tenant, status="Completed"),
                retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
                start_to_close_timeout=UpdateTenantStatusActivity.get_timeout(),
            )

            # send mail
            await workflow.execute_activity(
                activity=SendAfterProvisioningMailActivity.defn,
                arg=SendAfterProvisioningMailActivityModel(
                    realm_name=realm_name,
                    tenant=tenant,
                    user_details={
                        "firstName": first_name,
                        "lastName": last_name,
                        "email": email,
                    },
                    domain_name=zsegment_config.domain_name,
                    product=ProductName,
                    from_name=zsegment_config.sender_name,
                    email_from=zsegment_config.sender_email,
                ),
                retry_policy=SendAfterProvisioningMailActivity.get_retry_policy(),
                start_to_close_timeout=SendAfterProvisioningMailActivity.get_timeout(),
            )

        except Exception as e:
            workflow.logger.error(f"Error in onboarding workflow: {e}")
            await workflow.execute_activity(
                activity=UpdateTenantStatusActivity.defn,
                arg=TenantStatus(
                    tenant_name=tenant,
                    status="Failed",
                    error_msg=str(e),
                ),
                retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
                start_to_close_timeout=UpdateTenantStatusActivity.get_timeout(),
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
