from app.cli.temporal.models.onboard import OnboardInfo
from app.core.connections import get_lago_client
from app.models.lago.invoice import InvoiceResponse


def fetch_subscription_invoice(onboard_info: OnboardInfo) -> InvoiceResponse | None:
    """
    Fetch subscription invoice
    """
    lago_client = get_lago_client(onboard_info.product)
    invoices = lago_client.invoices().find_all({"external_customer_id": str(onboard_info.customer_id)})
    for invoice in invoices["invoices"]:
        invoice_resp = lago_client.invoices().find(invoice.lago_id)
        invoice = InvoiceResponse.from_lago(invoice_resp)
        if invoice.subscriptions.root[0].external_id == str(onboard_info.subscription_id):
            return invoice
    return None
