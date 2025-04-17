from app.cli.activity_utils.onboard.onboard_info import get_customer_onboard_info
from app.cli.keycloak_utils import KeycloakAdminClient
from app.cli.temporal.models.onboard import CustomerWorkflowInput
from app.core.connections import get_lago_client
from app.core.settings import get_settings
from app.mail_templates import provisioning_success_mail
from app.models.lago.customer import CustomerResponse
from app.models.product import ProductEnum
from app.route_utils.session_util import generate_password
from app.sendgrid_utils import send_mail

settings = get_settings()


def reset_keycloak_user_password(tenant_name: str, email: str, product: ProductEnum) -> str:
    """
    reset user temp password in keycloak
    """
    password = generate_password(10)

    keycloak_admin = KeycloakAdminClient(config=settings.keycloak)
    realm = f"{product.value.lower()}_{tenant_name}"

    keycloak_admin.refresh_token()
    users = keycloak_admin.get_users(realm_name=realm, query={"email": email})

    if len(users) != 1:
        if len(users) == 0:
            msg = f"OnboardingError: User {email} not found in realm {realm}"
        else:
            msg = f"OnboardingError: Found {len(users)} users with email {email} in realm {realm}"
        raise RuntimeError(msg)

    keycloak_admin.refresh_token()
    keycloak_admin.set_user_password(user_id=users[0]["id"], password=password, realm_name=realm)

    return password


async def send_customer_password_mail(
    name: str, email: str, tenantname: str, password: str, product: ProductEnum
) -> None:
    """
    Send password mail to customer
    """
    subject = f"Important: Your {product.value} Account Access is Here"
    app_config = ProductEnum.get_product_settings(product)
    content = provisioning_success_mail(
        name=name,
        email=email,
        link=f"https://{tenantname}.{app_config.tenant_fqdn}",
        password=password,
        product=product,
    )
    await send_mail(
        to_email=email,
        from_name=product.value,
        email_from=app_config.sendgrid.email_from,
        subject=subject,
        content=content,
    )


async def onboard_success(activity_input: CustomerWorkflowInput) -> None:
    """
    @return:
    """
    onboard_info = await get_customer_onboard_info(activity_input.customer_id, activity_input.product)
    lago_client = get_lago_client(onboard_info.product)
    customer_resp = lago_client.customers().find(str(onboard_info.customer_id))
    customer = CustomerResponse.from_lago(customer_resp)
    content = (
        f"Provisioning job details: <br> "
        f"name: {customer.name} <br> "
        f"email: {customer.email} <br> "
        f"tenantname: {onboard_info.tenant_name} <br> "
        f"customerId: {onboard_info.customer_id} <br> "
        f"status: {onboard_info.onboard_status.value} <br> "
    )

    password = reset_keycloak_user_password(onboard_info.tenant_name, customer.email, onboard_info.product)

    app_config = ProductEnum.get_product_settings(onboard_info.product)

    await send_mail(
        to_email=app_config.sendgrid.support_mail,
        from_name=onboard_info.product.value,
        email_from=app_config.sendgrid.email_from,
        subject=f"{onboard_info.tenant_name} {onboard_info.onboard_status.name}",
        content=content,
    )

    await send_customer_password_mail(
        name=customer.name,
        email=customer.email,
        tenantname=onboard_info.tenant_name,
        password=password,
        product=onboard_info.product,
    )
