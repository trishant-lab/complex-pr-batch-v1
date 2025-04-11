from app.cli.temporal.core.base import ScheduleWorkflow, Workflow
from app.cli.temporal.dexit.workflows.deprovisioning import DexitDeProvisioningWorkflow
from app.cli.temporal.dexit.workflows.onboarding import DexitOnboardingWorkflow
from app.cli.temporal.hdp.workflows.onboarding import HDPOnboardingWorkflow
from app.cli.temporal.jeeves.workflows.deprovisioning import JeevesDeProvisioningWorkflow
from app.cli.temporal.jeeves.workflows.onboarding import JeevesOnboardingWorkflow
from app.cli.temporal.muspell.workflows.onboarding import MuspellOnboardingWorkflow
from app.cli.temporal.penknife.workflows.deprovisioning import PenknifeDeProvisioningWorkflow
from app.cli.temporal.penknife.workflows.onboarding import PenknifeOnboardingWorkflow
from app.cli.temporal.practifly.workflows.deprovisioning import PractiflyDeProvisioningWorkflow
from app.cli.temporal.practifly.workflows.onboarding import PractiflyOnboardingWorkflow
from app.cli.temporal.pricedx.workflows.deprovisioning import PricedxDeProvisioningWorkflow
from app.cli.temporal.pricedx.workflows.onboarding import PricedxOnboardingWorkflow
from app.cli.temporal.veritable.workflows.deployment import VeritableDeploymentWorkflow
from app.cli.temporal.veritable.workflows.deprovisioning import VeritableDeProvisioningWorkflow
from app.cli.temporal.veritable.workflows.onboarding import VeritableOnboardingWorkflow
from app.cli.temporal.workflows.check_kube_config_certificate import KubeConfigCertExpiryWorkflow
from app.cli.temporal.workflows.onboard import OnboardWorkflow
from app.cli.temporal.workflows.payments.verify import OnboardPaymentVerifyWorkflow
from app.cli.temporal.workflows.webhooks.invoice import InvoiceWebhookEventWorkflow
from app.cli.temporal.zsegment.workflows.onboarding import ZSegmentOnboardingWorkflow

WORKFLOW_MAPPER: dict[str, type[Workflow | ScheduleWorkflow]] = {
    _workflow.__name__: _workflow
    for _workflow in [
        DexitOnboardingWorkflow,
        DexitDeProvisioningWorkflow,
        HDPOnboardingWorkflow,
        JeevesOnboardingWorkflow,
        JeevesDeProvisioningWorkflow,
        MuspellOnboardingWorkflow,
        PenknifeOnboardingWorkflow,
        PenknifeDeProvisioningWorkflow,
        PractiflyOnboardingWorkflow,
        PractiflyDeProvisioningWorkflow,
        ZSegmentOnboardingWorkflow,
        VeritableOnboardingWorkflow,
        OnboardWorkflow,
        OnboardPaymentVerifyWorkflow,
        InvoiceWebhookEventWorkflow,
        KubeConfigCertExpiryWorkflow,
        PricedxOnboardingWorkflow,
        PricedxDeProvisioningWorkflow,
        VeritableDeProvisioningWorkflow,
        VeritableDeploymentWorkflow,
    ]
}


async def schedule_workflows() -> None:
    """
    Schedule workflows
    """
    from app.cli.temporal.schedule_workflow_utils import remove_redundant_schedules
    from app.cli.temporal.starter import schedule_workflow
    from app.core.cli_settings import WorkerQueues

    await schedule_workflow(workflow=KubeConfigCertExpiryWorkflow, queue=WorkerQueues.kube_config_cert_expiry)
    await remove_redundant_schedules()


def main() -> None:
    """
    Main function
    """
    import asyncio

    asyncio.get_event_loop().run_until_complete(schedule_workflows())
