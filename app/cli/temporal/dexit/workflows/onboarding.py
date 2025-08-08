from .commonOnboardingScript import DexitCommonOnboardingWorkflow
from temporalio import workflow

@workflow.defn(name="DexitOnboardingWorkflow", sandboxed=False)
class DexitOnboardingWorkflow(DexitCommonOnboardingWorkflow):
    """
    Dexit Onboarding Workflow
    """

    def __init__(self: "DexitCommonOnboardingWorkflow") -> None:
        super().__init__(is_onboarding=True)
        self.approved: bool = False
        self.denied: bool = False

    @workflow.signal
    async def approve(self: "DexitCommonOnboardingWorkflow") -> None:
        """
        Signal to approve the workflow
        """
        self.approved = True

    @workflow.signal
    async def decline(self: "DexitCommonOnboardingWorkflow") -> None:
        """
        Signal to reject the workflow
        """
        self.denied = True
