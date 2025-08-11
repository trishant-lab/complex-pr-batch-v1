from .commonOnboardingScript import DexitCommonOnboardingWorkflow
from temporalio import workflow
from app.cli.temporal.dexit.models.dexit_spec import DexitSpec

@workflow.defn(name="DexitDeploymentWorkflow", sandboxed=False)
class DexitDeploymentWorkflow(DexitCommonOnboardingWorkflow):
    """
    Dexit Onboarding Workflow
    """

    def __init__(self: "DexitCommonOnboardingWorkflow") -> None:
        super().__init__(is_onboarding=False)

    @workflow.run
    async def run(self: "DexitCommonOnboardingWorkflow", dexit: DexitSpec) -> None:
        """
        Run the workflow
        """
        await super().run(dexit)