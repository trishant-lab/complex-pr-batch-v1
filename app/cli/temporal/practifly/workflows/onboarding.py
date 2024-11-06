from collections.abc import Callable
from temporalio import workflow
import pydash

from app.cli.temporal.activities.updateTenantStatus import TenantStatus, UpdateTenantStatusActivity
from app.cli.temporal.core.base import Workflow
from app.cli.temporal.practifly.models.practiflySpec import PractiflySpec


with workflow.unsafe.imports_passed_through():
    from app.core.settings import AppSettings, PractiflySettings, get_settings


ProductName = "practifly"
OnePasswordVaultName = "practifly"


@workflow.defn(name="PractiflyOnboardingWorkflow", sandboxed=False)
class PractiflyOnboardingWorkflow(Workflow):
    """
    Practifly Onboarding Workflow
    """

    def __init__(self: "Workflow") -> None:
        self.approved: bool = False
        self.deny: bool = False

    @staticmethod
    def get_activities() -> list[type[Callable]]:  # type: ignore
        """
        Return list of activities used in the workflow
        """
        return []

    @workflow.run
    async def run(self: "Workflow", practifly: PractiflySpec) -> None:
        """
        Run the workflow
        """
        config: AppSettings = get_settings()
        practifly_config: PractiflySettings = config.practifly

        tenant = pydash.get(practifly, "tenant")

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

    @workflow.signal
    async def approve(self: "Workflow") -> None:
        """
        Approve the workflow
        """
        self.approved = True

    @workflow.signal
    async def deny(self: "Workflow") -> None:
        """
        Deny the workflow
        """
        self.deny = True
