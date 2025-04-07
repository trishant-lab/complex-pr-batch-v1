import uuid
from collections.abc import Callable

from loguru import logger
from temporalio import workflow

from app.cli.activity_util import run_activity
from app.cli.temporal.activities.invoice import FirstInvoicePollActivity, FirstInvoiceStatusPollActivity
from app.cli.temporal.activities.onboard.status import OnboardStatusActivity
from app.cli.temporal.activities.onboard.trigger import OnboardWorkflowTriggerActivity
from app.cli.temporal.activities.payments.failure import OnboardPaymentFailureActivity
from app.cli.temporal.activities.subscribe import SubscriptionActivity, SubscriptionCleanupActivity
from app.cli.temporal.core.base import Workflow
from app.cli.temporal.core.exceptions import NonRetryableException
from app.cli.temporal.models.onboard import CustomerWorkflowInput, OnboardInfo
from app.models.billing_models import PaymentStatus
from app.models.tenant import TenantStatusEnum


@workflow.defn
class OnboardPaymentVerifyWorkflow(Workflow):
    @staticmethod
    def get_activities() -> list[type[Callable]]:
        """
        Return list of activities used in the workflow
        """
        return [
            OnboardStatusActivity.defn,
            SubscriptionActivity.defn,
            FirstInvoicePollActivity.defn,
            OnboardPaymentFailureActivity.defn,
            OnboardWorkflowTriggerActivity.defn,
            FirstInvoiceStatusPollActivity.defn,
            SubscriptionCleanupActivity.defn,
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
        onboard_info: OnboardInfo = await run_activity(OnboardStatusActivity, workflow_input)

        if onboard_info.onboard_status == TenantStatusEnum.Provisioned:
            # already onboarded
            return

        await run_activity(SubscriptionActivity, onboard_info)

        # check finalized invoice generation
        onboard_info = await run_activity(FirstInvoicePollActivity, onboard_info)

        # poll invoice status
        onboard_info = await run_activity(FirstInvoiceStatusPollActivity, onboard_info)

        match onboard_info.invoice.payment_status:
            case PaymentStatus.failed:
                await run_activity(OnboardPaymentFailureActivity, onboard_info)
                await run_activity(SubscriptionCleanupActivity, onboard_info)
            case PaymentStatus.succeeded:
                # start onboard workflow
                await run_activity(OnboardWorkflowTriggerActivity, workflow_input)
            case _:
                msg = f"Unknown Invoice payment status {onboard_info.invoice.payment_status}"
                logger.error(msg)
                raise NonRetryableException(msg)
