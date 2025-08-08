from .commonOnboardingScript import DexitCommonOnboardingWorkflow
from temporalio import workflow

@workflow.defn(name="DexitDeploymentWorkflow", sandboxed=False)
class DexitDeploymentWorkflow(DexitCommonOnboardingWorkflow):
    """
    Dexit Onboarding Workflow
    """

    def __init__(self: "DexitCommonOnboardingWorkflow") -> None:
        super().__init__(is_onboarding=False)