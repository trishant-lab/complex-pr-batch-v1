from app.cli.penknife.models.penknifespec import PenknifeSpec
from app.cli.temporal.core.base import LaunchpadCLIBaseModel, Workflow
from temporalio import workflow


@Workflow.defn
class PenknifeOnboardingWorkflow(Workflow):
    """
    Penknife Onboarding Workflow
    """

    def __init__(self: "Workflow") -> None:
        self.approved: bool = False
        self.deny: bool = False

    @classmethod
    def get_workflow_id(cls: "Workflow", penfknife: PenknifeSpec) -> str :
        """
        Return workflow id
        """
        return f"penknife_onboarding_workflow_{penfknife.tenant}"
    
    @Workflow.run
    async def run(self: "Workflow", penknife: PenknifeSpec) -> None:
        """
        Run workflow
        """
        try:
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
