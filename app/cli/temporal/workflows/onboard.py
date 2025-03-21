import uuid
from collections.abc import Callable

from temporalio import workflow

from app.cli.activity_util import run_activity
from app.cli.temporal.activities.onboard.failure import OnboardFailureMailActivity
from app.cli.temporal.activities.onboard.k8s import ProvisioningK8SActivity
from app.cli.temporal.activities.onboard.status import OnboardStatusActivity, PollOnboardStatusActivity
from app.cli.temporal.activities.onboard.success import OnboardSuccessMailActivity
from app.cli.temporal.core.base import Workflow
from app.cli.temporal.exceptions.onboard import InvalidOnboardStatusException
from app.cli.temporal.models.onboard import CustomerWorkflowInput, OnboardInfo
from app.models.tenant import TenantStatusEnum


@workflow.defn
class OnboardWorkflow(Workflow):
    @staticmethod
    def get_activities() -> list[type[Callable]]:
        """
        Return list of activities used in the workflow
        """
        return [
            OnboardStatusActivity.defn,
            ProvisioningK8SActivity.defn,
            PollOnboardStatusActivity.defn,
            OnboardFailureMailActivity.defn,
            OnboardSuccessMailActivity.defn,
        ]

    @classmethod
    def get_workflow_id(cls: type["Workflow"], workflow_input: CustomerWorkflowInput) -> str | None:
        """
        Return unique workflow id from workflow input, guarantees exactly one execution of workflow
        """
        return str(uuid.uuid5(uuid.NAMESPACE_OID, cls.__name__.lower() + str(workflow_input.customer_id)))

    @workflow.run
    async def run(self: "Workflow", workflow_input: CustomerWorkflowInput) -> None:
        """
        Run the workflow
        """
        # fetch onboarding status
        onboard_info: OnboardInfo = await run_activity(activity=OnboardStatusActivity, arg=workflow_input)

        if onboard_info.onboard_status not in {TenantStatusEnum.Provisioning, TenantStatusEnum.Failed}:
            msg = f"Invalid onboarding status: {onboard_info.onboard_status}"
            raise InvalidOnboardStatusException(msg)

        # create k8s resource
        await run_activity(activity=ProvisioningK8SActivity, arg=onboard_info)

        onboard_info = await run_activity(activity=PollOnboardStatusActivity, arg=workflow_input)

        match onboard_info.onboard_status:
            case TenantStatusEnum.Provisioned:
                await run_activity(activity=OnboardSuccessMailActivity, arg=onboard_info)
            case TenantStatusEnum.Failed:
                await run_activity(activity=OnboardFailureMailActivity, arg=onboard_info)
            case _:
                msg = f"Unknown onboarding status after polling: {onboard_info.onboard_status}"
                raise InvalidOnboardStatusException(msg)
