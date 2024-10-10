from tempfile import TemporaryDirectory

from app.cli.keycloakUtils import KeycloakAdminClient
from app.cli.temporal.core.log import log_error, log_info
from app.common import generate_password
from app.core.db import DBManager, get_db_manager
from app.core.settings import AppSettings, get_settings
from app.sendgrid_utils import send_mail
from app.template_env import get_env


async def provisioning_success_mail(name: str, email: str, link: str, password: str, email_template: str) -> str:
    """
    @param name:
    @param email:
    @param link:
    @param password:
    @param email_template:
    @return:
    """
    with TemporaryDirectory() as temp_dir:
        with open(f"{temp_dir}/provisioning_success_mail.html", "w") as f:
            f.write(email_template)

        template_env = get_env(template_path=temp_dir)
        template = template_env.get_template("provisioning_success_mail.html")
        return template.render(
            user_name=name,
            email=email,
            environment_link=link,
            password=password,
        )


async def send_customer_password_mail(
    tenant: str, user_details: dict, domain_name: str, product: str, password: str, from_name: str, email_from: str
) -> None:
    """
    Send password mail to customer
    """
    config: AppSettings = get_settings()

    db: DBManager = await get_db_manager(config.postgres.dsn)

    # get template
    try:
        response = await db.fetch_one(
            "getEmailTemplateByProduct.sql", product=product, template_name="AfterProvisioning"
        )
        response = dict(response)
    except Exception as e:
        log_error(f"Error fetching template: {e}")
        raise Exception("Error fetching email template")

    subject = response["subject"]
    content = await provisioning_success_mail(
        name=f"{user_details.get('firstName')} {user_details.get('lastName')}",
        email=user_details.get("email"),
        link=f"https://{tenant}.{domain_name}",
        password=password,
        email_template=response["template"],
    )
    send_mail(
        to_email=user_details.get("email"),
        subject=subject,
        content=content,
        from_name=from_name,
        email_from=email_from,
    )


def reset_keycloak_user_password(realm_name: str, email: str, password: str) -> str:
    """
    reset user temp password in keycloak
    """
    config: AppSettings = get_settings()

    keycloak_admin_client = KeycloakAdminClient(config=config.keycloak)

    users = keycloak_admin_client.get_users(query={"email": email}, realm_name=realm_name)

    if len(users) != 1:
        if len(users) == 0:
            msg = f"OnboardingError: User {email} not found in realm {realm_name}"
        else:
            msg = f"OnboardingError: Found {len(users)} users with email " f"{email} in realm {realm_name}"
        raise Exception(msg)

    keycloak_admin_client.set_user_password(user_id=users[0]["id"], password=password, realm_name=realm_name)

    return password


async def send_provisioning_mail(
    tenant: str, realm_name: str, user_details: dict, domain_name: str, product: str, from_name: str, email_from: str
) -> None:
    """
    @return:
    """
    password = generate_password(10)
    reset_keycloak_user_password(realm_name=realm_name, email=user_details.get("email"), password=password)
    await send_customer_password_mail(
        tenant=tenant,
        user_details=user_details,
        domain_name=domain_name,
        product=product,
        password=password,
        from_name=from_name,
        email_from=email_from,
    )

    log_info(f"Tenant temporary credentials were sent {user_details.get('email')}")
    return


async def send_before_provisioning_mail(user_details: dict, product: str, from_name: str, email_from: str) -> None:
    """
    Send mail to customer before provisioning
    """
    config: AppSettings = get_settings()
    db: DBManager = await get_db_manager(config.postgres.dsn)

    # get template
    try:
        response = await db.fetch_one(
            "getEmailTemplateByProduct.sql", product=product, template_name="BeforeProvisioning"
        )
        response = dict(response)
    except Exception as e:
        log_error(f"Error fetching template: {e}")
        raise Exception("Error fetching email template")

    subject = response["subject"]

    with TemporaryDirectory() as temp_dir:
        with open(f"{temp_dir}/before_provisioning_mail.html", "w") as f:
            f.write(response["template"])

        template_env = get_env(template_path=temp_dir)
        template = template_env.get_template("before_provisioning_mail.html")
        content = template.render(
            user_name=f"{user_details.get('firstName')} {user_details.get('lastName')}",
        )

    send_mail(
        to_email=user_details.get("email"),
        subject=subject,
        content=content,
        from_name=from_name,
        email_from=email_from,
    )
    log_info(f"Sent before provisioning mail to {user_details.get('email')}")
