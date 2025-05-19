from typing import TYPE_CHECKING

import pendulum

from app.cli.activity_utils.payments.invoice_file import get_invoice_helper
from app.cli.temporal.core.exceptions import NonRetryableException
from app.core.connections import get_lago_client
from app.core.db import get_db_manager
from app.mail_templates.main import periodic_invoice_mail
from app.models.enums import SubscriptionType
from app.models.lago.invoice import InvoiceResponse
from app.models.lago.plan import PlanResponse
from app.models.product import ProductEnum
from app.sendgrid_utils import send_mail

if TYPE_CHECKING:
    from app.models.lago.invoice_item import InvoiceItemResponse
    from app.models.lago.subscription import SubscriptionResponse


def get_plan_price_per_day(product: ProductEnum, plan_code: str) -> float:
    """
    @param plan_code:
    @return: return price of the plan per day
    """
    client = get_lago_client(product)
    plan_resp = client.plans().find(plan_code)
    plan = PlanResponse.from_lago(plan_resp)
    match plan.interval:
        case "monthly":
            return plan.amount_cents / 30
        case "yearly":
            return plan.amount_cents / 365
        case "quarterly":
            return plan.amount_cents / 90
        case "weekly":
            return plan.amount_cents / 7
        case _:
            msg = f"Invalid plan interval: {plan.interval}"
            raise NonRetryableException(msg)


def get_subscription_type(product: ProductEnum, current_plan: str, previous_plan: str) -> SubscriptionType:
    """
    @return: return subscription type based on price of plans
    """
    current_plan_price = get_plan_price_per_day(product, current_plan)
    previous_plan_price = get_plan_price_per_day(product, previous_plan)

    if current_plan_price > previous_plan_price:
        return SubscriptionType.upgrade
    if current_plan_price < previous_plan_price:
        return SubscriptionType.downgrade

    return SubscriptionType.renewal


def prepare_invoice_mail_content(
    product: ProductEnum, customer_id: str, data: InvoiceResponse, tenant_link: str | None
) -> tuple[SubscriptionType, str]:
    """
    @param tenant_link:
    @param customer_id:
    @param data:
    @return subject, content:
    """
    try:
        item: InvoiceItemResponse = next(fee.item for fee in data.fees.root if fee.item.type == "subscription")
    except StopIteration:
        msg = "No subscription found in invoice"
        raise NonRetryableException(msg)

    subscription: SubscriptionResponse = next(sub for sub in data.subscriptions.root if sub.plan_code == item.code)

    client = get_lago_client(product)
    invoices = client.invoices().find_all(
        {
            "payment_status": "succeeded",
            "external_customer_id": customer_id,
            "invoice_type": "subscription",
        }
    )

    if invoices["meta"]["total_count"] > 1:
        subscription_type = (
            get_subscription_type(product, subscription.plan_code, subscription.previous_plan_code)
            if len(data.subscriptions.root) > 1
            else SubscriptionType.renewal
        )
    else:
        subscription_type = SubscriptionType.initial

    subscription_at = pendulum.parse(subscription.subscription_at)
    if "_m_" in item.code:
        renew_date = subscription_at.add(months=pendulum.now("UTC").diff(subscription_at).in_months() + 1)
        interval = "monthly"
    else:
        renew_date = subscription_at.add(years=pendulum.now("UTC").diff(subscription_at).in_years() + 1)
        interval = "yearly"

    _data = {
        "product": product,
        "name": data.customer.name,
        "plan_name": item.name,
        "plan_interval": interval.capitalize(),
        "renew_date": renew_date.date().__str__(),
        "subscription_type": subscription_type,
        "tenant_link": tenant_link,
    }
    content = periodic_invoice_mail(**_data)

    return subscription_type, content


def prepare_invoice_mail_subject(product: ProductEnum, subscription_type: SubscriptionType) -> str:
    """
    @param subscription_type:
    @return: subject based on subscription type
    """
    match subscription_type:
        case SubscriptionType.initial:
            return f"Important: Payment Received - {product.value} Subscription Confirmation"
        case SubscriptionType.upgrade:
            return f"{product.value} Subscription Update: Account Upgraded"
        case SubscriptionType.renewal | SubscriptionType.downgrade:
            return f"{product.value} Subscription Renewal: Payment Confirmation"
        case _:
            msg = f"Invalid subscription type: {subscription_type}"
            raise NonRetryableException(msg)


def download_invoice(product: ProductEnum, lago_id: str) -> InvoiceResponse:
    """
    @param lago_id:
    @return:
    """
    client = get_lago_client(product)
    invoice_resp = client.invoices().download(lago_id)
    return InvoiceResponse.from_lago(invoice_resp)


async def payment_success_service(product: ProductEnum, invoice: InvoiceResponse) -> None:
    """
    @param invoice:
    send success mail
    """
    client = get_lago_client(product)
    app_config = ProductEnum.get_product_settings(product)

    invoice_resp = client.invoices().find(invoice.lago_id)
    invoice_data = InvoiceResponse.from_lago(invoice_resp)
    customer_id = invoice_data.customer.external_id

    subscription_id = invoice_data.subscriptions.root[0].external_id

    db = await get_db_manager()
    params = {
        "table": "subscription s",
        "join_table": "customer c",
        "join_on": "s.customerid=c.id",
        "where": f"s.id='{subscription_id!s}'",
        "columns": ["c.tenantname"],
    }
    subscription = await db.fetch_one("get.sql", **params)

    if not subscription:
        msg = "Payment Succeeded for non existent subscription"
        raise NonRetryableException(msg)

    tenant_name = subscription.get("tenantname")
    if tenant_name:
        tenant_link = f"https://{tenant_name}.{app_config.tenant_fqdn}"
    else:
        tenant_link = None

    subscription_type, content = prepare_invoice_mail_content(product, customer_id, invoice_data, tenant_link)
    subject = prepare_invoice_mail_subject(product, subscription_type)

    _invoice: dict = get_invoice_helper(product, invoice.model_dump())

    await send_mail(
        to_email=invoice_data.customer.email,
        email_from=app_config.sendgrid.email_from,
        bcc_email=(
            app_config.sendgrid.support_mail
            if subscription_type not in [SubscriptionType.renewal, SubscriptionType.downgrade]
            else None
        ),
        from_name=product.value,
        subject=subject,
        content=content,
        attachments=[_invoice["file_url"]],
        attachment_with_url=True,
    )
