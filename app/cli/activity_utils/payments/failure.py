import uuid
from urllib.parse import urljoin

import stripe

from app.cli.activity_utils.payments.stripe_status import get_stripe_failure_status
from app.cli.temporal.models.onboard import OnboardInfo
from app.core.connections import get_lago_client
from app.core.db import DBManager, get_db_manager
from app.core.settings import get_settings
from app.mail_templates import internal_payment_failure_mail, payment_failure_mail
from app.mail_templates.main import internal_renewal_payment_failure_mail
from app.models.billing_models import PaymentStatus
from app.models.lago.customer import CustomerResponse
from app.models.lago.plan import PlanResponse
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum
from app.sendgrid_utils import send_mail

settings = get_settings()


async def send_internal_renewal_payment_failure_mail(
    customer: CustomerResponse, tenant_name: str, product: ProductEnum
) -> None:
    """
    @return:
    """
    app_config = ProductEnum.get_product_settings(product)
    internal_content = internal_renewal_payment_failure_mail(customer, tenant_name, product)
    subject = f"[{product.value}] Action Required: Renewal Payment failure for {tenant_name}"
    await send_mail(
        to_email=app_config.sendgrid.support_mail,
        email_from=app_config.sendgrid.email_from,
        subject=subject,
        content=internal_content,
        from_name=product.value,
    )


async def payment_failure(customer_id: uuid.UUID, product: ProductEnum) -> None:
    """
    @param customer_id:
    @return:
    """
    db = await get_db_manager()
    params = {
        "table": "provisioningstatus s",
        "join_table": "customer c",
        "join_on": "c.id=s.customerid",
        "where": f"s.customerid='{customer_id!s}'",
        "columns": ["s.status", "c.tenantname", "c.id"],
    }
    plan_params = {
        "table": "subscription",
        "where": f"customerid='{customer_id!s}'",
        "columns": ["plancode"],
    }
    customer, plan = await db.fetch_many([("get.sql", params), ("get.sql", plan_params)])  # NOSONAR
    customer = customer[0]
    plan_code = plan[0]["plancode"]
    tenant_name = customer["tenantname"]
    lago_client = get_lago_client(product)
    _customer_resp = lago_client.customers().find(str(customer["id"]))
    _customer = CustomerResponse.from_lago(_customer_resp)
    app_config = ProductEnum.get_product_settings(product)

    if customer["status"] == TenantStatusEnum.Provisioned:
        subject = f"Payment Failure: Update Your Payment Method Now - {product.value}"
        fqdn = f"{app_config.tenant_fqdn}/sprint" if app_config.tenant_fqdn.endswith("work") else app_config.tenant_fqdn
        accounts_link = f"{tenant_name}.{fqdn}/accounts"
        plan_resp = lago_client.plans().find(plan_code)
        plan = PlanResponse.from_lago(plan_resp)
        content = payment_failure_mail(
            name=_customer.name, retry_link=accounts_link, plan_name=plan.name, product=product
        )

        await send_mail(
            to_email=_customer.email,
            bcc_email=app_config.sendgrid.support_mail,
            subject=subject,
            content=content,
            email_from=app_config.sendgrid.email_from,
            from_name=product.value,
        )

    await send_internal_renewal_payment_failure_mail(_customer, tenant_name, product)


async def send_retry_mail(customer: CustomerResponse, onboard_info: OnboardInfo) -> None:
    """
    Send payment retry link to customer
    """
    product: ProductEnum = onboard_info.product
    lago_client = get_lago_client(product)
    app_config = ProductEnum.get_product_settings(product)
    plan_resp = lago_client.plans().find(onboard_info.subscription_plan)
    plan = PlanResponse.from_lago(plan_resp)

    subject = f"Payment Failure: Update Your Payment Method Now - {product.value}"
    retry_link = urljoin(
        app_config.signup_url.__str__(),
        f"/pricing/?email={customer.email}&plan={onboard_info.subscription_plan}",
    )
    content = payment_failure_mail(customer.name, retry_link, plan.name, product)
    await send_mail(
        to_email=customer.email,
        email_from=app_config.sendgrid.email_from,
        bcc_email=app_config.sendgrid.support_mail,
        subject=subject,
        content=content,
        from_name=product.value,
    )


async def reset_setup_intent(onboard_info: OnboardInfo, customer: CustomerResponse, db: DBManager) -> None:
    """
    Delete old payment method
    get setup intent from lago cust meta,
    cancel the setup intent,
    create new setup intent and save it in meta in lago customer
    send mail with link for adding payment method with setup intent (work with FE team)
    """
    customer_id = onboard_info.customer_id
    setup_intent_key = (await db.fetch_one("get.sql", table="customer", where=f"id='{customer_id!s}'"))["setupintent"]
    stripe_secret_key = ProductEnum.get_stripe_secret_key(onboard_info.product)

    _setup_intent = await stripe.SetupIntent.create_async(
        api_key=stripe_secret_key,
        customer=customer.billing_configuration.provider_customer_id,
        payment_method_types=["card"],
        idempotency_key=setup_intent_key,
    )
    setup_intent = await stripe.SetupIntent.retrieve_async(
        id=_setup_intent.id,
        api_key=stripe_secret_key,
    )
    # payment method addition was successful, but payment has failed, create new setup intent idem key, save in lago
    if setup_intent.status in {"success", "succeeded", "canceled"}:
        setup_intent_key = str(uuid.uuid4())
        intent_params = {
            "table": "customer",
            "where": f"id='{customer_id!s}'",
            "payload": {"setupintent": setup_intent_key},
        }
        provisioned_params = {
            "table": "provisioningstatus",
            "where": f"customerid='{customer_id!s}'",
            "payload": {"status": TenantStatusEnum.NotApplicable.value},
        }
        await db.execute_many([("put.sql", intent_params), ("put.sql", provisioned_params)])  # NOSONAR

    await stripe.SetupIntent.create_async(
        api_key=stripe_secret_key,
        customer=customer.billing_configuration.provider_customer_id,
        payment_method_types=["card"],
        idempotency_key=setup_intent_key,
    )


async def send_internal_onboard_payment_failure_mail(customer: CustomerResponse, product: ProductEnum) -> None:
    """
    @param customer:
    @return:
    """
    internal_content = internal_payment_failure_mail(customer, product)
    subject = f"[{product.value}] No Action Required: Customer Payment failure"
    match product:
        case ProductEnum.veritable:
            to_email = settings.veritable.sendgrid.support_mail
            email_from = settings.veritable.sendgrid.email_from
        case _:
            to_email = settings.sendgrid.support_mail
            email_from = settings.sendgrid.email_from
    await send_mail(
        to_email=to_email,
        email_from=email_from,
        subject=subject,
        content=internal_content,
        from_name=product.value,
    )


async def onboard_payment_failure(onboard_info: OnboardInfo) -> None:
    """
    @param onboard_info:
    @return:
    """
    db = await get_db_manager()
    lago_client = get_lago_client(onboard_info.product)
    _existing_invoice = await db.fetch_one(
        "get.sql",
        table="failedinvoices",
        where=f"invoiceid='{onboard_info.invoice.lago_id}' ",
    )
    customer_resp = lago_client.customers().find(str(onboard_info.customer_id))
    customer = CustomerResponse.from_lago(customer_resp)

    stripe_customer_id = customer.billing_configuration.provider_customer_id
    stripe_failure_reason = await get_stripe_failure_status(
        stripe_customer_id, onboard_info.invoice.lago_id, onboard_info.product
    )
    if _existing_invoice:
        await db.execute(
            "put.sql",
            table="failedinvoices",
            where=f"invoiceid='{onboard_info.invoice.lago_id}' ",
            payload={"paymentstatus": PaymentStatus.failed.value, "reason": stripe_failure_reason},
        )
    else:
        await db.execute(
            "post.sql",
            table="failedinvoices",
            payload={
                "invoiceid": onboard_info.invoice.lago_id,
                "customerid": onboard_info.customer_id,
                "subscriptionid": onboard_info.subscription_id,
                "paymentstatus": PaymentStatus.failed.value,
                "reason": stripe_failure_reason,
            },
        )

    await reset_setup_intent(onboard_info, customer, db)

    await send_internal_onboard_payment_failure_mail(customer, onboard_info.product)
    await send_retry_mail(customer, onboard_info)
