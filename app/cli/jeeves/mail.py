from tempfile import TemporaryDirectory

from app.cli.common.keycloakUtils import KeycloakAdminClient
from app.cli.jeeves.models.jeevesSpec import JeevesSpec
from app.cli.temporal.core.log import log_info, log_error
from app.common import generate_password
from app.core.db import get_db_manager, DBManager
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


async def send_customer_password_mail(jeeves: JeevesSpec, password: str) -> None:
    """
    Send password mail to customer
    """
    config: AppSettings = get_settings()
    domain_name: str = config.jeeves.domain_name

    db: DBManager = await get_db_manager(config.postgres.dsn)

    # get template
    try:
        response = await db.fetch_one(
            "getEmailTemplateByProduct.sql", product="Jeeves", template_name="AfterProvisioning"
        )
        response = dict(response)
    except Exception as e:
        log_error(f"Error fetching template: {e}")
        raise Exception("Error fetching email template")

    subject = response["subject"]
    content = await provisioning_success_mail(
        name=f"{jeeves.firstName} {jeeves.lastName}",
        email=jeeves.email,
        link=f"https://{jeeves.tenant}.{domain_name}",
        password=password,
        email_template=response["template"],
    )
    send_mail(to_email=jeeves.email, subject=subject, content=content, from_name="314e Support")


def reset_keycloak_user_password(jeeves: JeevesSpec, password: str) -> str:
    """
    reset user temp password in keycloak
    """
    config: AppSettings = get_settings()

    keycloak_admin_client = KeycloakAdminClient(config=config.keycloak)
    realm_name = jeeves.tenant

    users = keycloak_admin_client.get_users(query={"email": jeeves.email}, realm_name=realm_name)

    if len(users) != 1:
        if len(users) == 0:
            msg = f"OnboardingError: User {jeeves.email} not found in realm {realm_name}"
        else:
            msg = f"OnboardingError: Found {len(users)} users with email " f"{jeeves.email} in realm {realm_name}"
        raise Exception(msg)

    keycloak_admin_client.set_user_password(user_id=users[0]["id"], password=password, realm_name=realm_name)

    return password


async def onboard_success(jeeves: JeevesSpec) -> None:
    """
    @return:
    """
    password = generate_password(10)
    reset_keycloak_user_password(jeeves=jeeves, password=password)
    await send_customer_password_mail(jeeves=jeeves, password=password)

    log_info(f"Tenant temporary credentials were sent {jeeves.email}")
    return
