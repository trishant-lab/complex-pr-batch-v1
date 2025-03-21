from collections.abc import Callable
from uuid import UUID, uuid4

from loguru import logger
from temporalio import workflow

from app.cli.activity_util import run_activity
from app.cli.temporal.activities.payments.check_enterprise import CheckEnterpriseActivity
from app.cli.temporal.activities.payments.failure import PaymentFailureActivity
from app.cli.temporal.activities.payments.success import PaymentSuccessActivity, PaymentSuccessActivityInput
from app.cli.temporal.core.base import Workflow
from app.cli.temporal.models.onboard import CustomerWorkflowInput
from app.cli.temporal.models.webhooks.invoice import InvoiceWebhookEvent, InvoiceWebhookType
from app.models.billing_models import PaymentStatus


@workflow.defn
class InvoiceWebhookEventWorkflow(Workflow):
    @staticmethod
    def get_activities() -> list[type[Callable]]:
        """
        @return:
        """
        return [
            CheckEnterpriseActivity.defn,
            PaymentFailureActivity.defn,
            PaymentSuccessActivity.defn,
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", workflow_input: InvoiceWebhookEvent) -> str | None:
        """
        Invoice Webhook event, all webhooks need to be processed, even in case of resubmissions
        """
        return str(uuid4())

    @workflow.run
    async def run(self: "Workflow", workflow_input: InvoiceWebhookEvent) -> None:
        """
        Workflow to process incoming invoice events
        """
        # nested models are not parsed
        if await run_activity(CheckEnterpriseActivity, workflow_input):
            return
        workflow_input = InvoiceWebhookEvent.model_validate(workflow_input)

        match workflow_input.webhook_type:
            case InvoiceWebhookType.payment_status_updated:
                lago_id = UUID(workflow_input.invoice.lago_id)
                customer_id = UUID(workflow_input.invoice.customer.external_id)
                match workflow_input.invoice.payment_status:
                    case PaymentStatus.succeeded:
                        _arg = PaymentSuccessActivityInput(lago_id=lago_id, product=workflow_input.product)
                        await run_activity(PaymentSuccessActivity, _arg)
                    case PaymentStatus.failed:
                        _arg = CustomerWorkflowInput(customer_id=customer_id, product=workflow_input.product)
                        await run_activity(PaymentFailureActivity, _arg)
                    case _:
                        msg = f"ignored invoice payment status: {workflow_input.invoice.payment_status}"
                        logger.warning(msg)
            case InvoiceWebhookType.payment_failure:
                customer_id = UUID(workflow_input.payment_provider_invoice_payment_error.external_customer_id)
                _arg = CustomerWorkflowInput(customer_id=customer_id, product=workflow_input.product)
                await run_activity(PaymentFailureActivity, _arg)
            case _:
                msg = f"ignored invoice webhook type: {workflow_input.webhook_type}"
                logger.warning(msg)
