from app.cli.temporal.models.onboard import OnboardInfo
from app.core.connections import get_lago_client
from app.core.db import DBManager, get_db_manager
from app.mail_templates import provisioning_failure_mail
from app.models.lago.customer import CustomerResponse
from app.models.lago.plan import PlanResponse
from app.models.product import ProductEnum
from app.sendgrid_utils import send_mail


async def send_customer_onboard_failure_mail(email: str, name: str, plan_name: str, product: ProductEnum) -> None:
    """
    @param email:
    @param name:
    @param plan_name:
    @return:
    """
    app_config = ProductEnum.get_product_settings(product)
    subject = f"Payment Successful! Environment Creation In Progress - {product.value}"
    content = provisioning_failure_mail(name=name, plan_name=plan_name, product=product)
    await send_mail(
        to_email=email,
        from_name=product.value,
        email_from=app_config.sendgrid.email_from,
        subject=subject,
        content=content,
    )


async def onboard_failure(onboard_info: OnboardInfo) -> None:
    """
    @param onboard_info:
    @return:
    """
    db: DBManager = await get_db_manager()
    errors = await db.fetch_one("get.sql", table="operatorstatus", where=f"customerid='{onboard_info.customer_id}'")
    lago_client = get_lago_client(onboard_info.product)
    customer_resp = lago_client.customers().find(str(onboard_info.customer_id))
    customer = CustomerResponse.from_lago(customer_resp)
    content = (
        f"Provisioning job details: <br> "
        f"name: {customer.name} <br> "
        f"email: {customer.email} <br> "
        f"tenantname: {onboard_info.tenant_name} <br> "
        f"customerId: {onboard_info.customer_id} <br> "
        f"status: {onboard_info.onboard_status.value} <br>"
        f"errors: {errors['errors']}"
    )

    app_config = ProductEnum.get_product_settings(onboard_info.product)

    await send_mail(
        to_email=app_config.sendgrid_support_mail,
        from_name=onboard_info.product.value,
        email_from=app_config.sendgrid_from_mail,
        subject=f"{onboard_info.tenant_name} provisioning {onboard_info.onboard_status.name}",
        content=content,
    )

    plan_resp = lago_client.plans().find(onboard_info.subscription_plan)
    plan = PlanResponse.from_lago(plan_resp)
    await send_customer_onboard_failure_mail(
        name=customer.name,
        email=customer.email,
        plan_name=plan.name,
        product=onboard_info.product,
    )
