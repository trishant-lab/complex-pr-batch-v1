from app.cli.temporal.core.base import ScheduleWorkflow, Workflow
from app.cli.temporal.dexit.workflows.deprovisioning import DexitDeProvisioningWorkflow
from app.cli.temporal.dexit.workflows.onboarding import DexitOnboardingWorkflow
from app.cli.temporal.hdp.workflows.onboarding import HDPOnboardingWorkflow
from app.cli.temporal.jeeves.workflows.deprovisioning import JeevesDeProvisioningWorkflow
from app.cli.temporal.jeeves.workflows.onboarding import JeevesOnboardingWorkflow
from app.cli.temporal.penknife.workflows.deprovisioning import PenknifeDeProvisioningWorkflow
from app.cli.temporal.penknife.workflows.onboarding import PenknifeOnboardingWorkflow
from app.cli.temporal.practifly.workflows.deprovisioning import PractiflyDeProvisioningWorkflow
from app.cli.temporal.practifly.workflows.onboarding import PractiflyOnboardingWorkflow
from app.cli.temporal.veritable.workflows.onboarding import VeritableOnboardingWorkflow
from app.cli.temporal.zsegment.workflows.onboarding import ZSegmentOnboardingWorkflow

WORKFLOW_MAPPER: dict[str, type[Workflow | ScheduleWorkflow]] = {
    _workflow.__name__: _workflow
    for _workflow in [
        DexitOnboardingWorkflow,
        DexitDeProvisioningWorkflow,
        JeevesOnboardingWorkflow,
        JeevesDeProvisioningWorkflow,
        HDPOnboardingWorkflow,
        PenknifeOnboardingWorkflow,
        PenknifeDeProvisioningWorkflow,
        PractiflyOnboardingWorkflow,
        PractiflyDeProvisioningWorkflow,
        ZSegmentOnboardingWorkflow,
        VeritableOnboardingWorkflow,
    ]
}
