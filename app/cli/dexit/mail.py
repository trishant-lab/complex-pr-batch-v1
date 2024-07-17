from app.cli.dexit import TemplatePath
from app.cli.dexit.models.dexitSpec import DexitSpec
from app.cli.common.keycloakUtils import KeycloakAdminClient
from app.cli.temporal.core.log import log_info
from app.common import generate_password
from app.core.settings import AppSettings, get_settings
from app.sendgrid_utils import send_mail
from app.template_env import get_env


def provisioning_success_mail(name: str, email: str, link: str, password: str) -> str:
    """
    @param name:
    @param email:
    @param link:
    @param password:
    @return:
    """
    env = get_env(template_path=TemplatePath)
    template = env.get_template("provisioning_success_mail.html")
    return template.render(
        user_name=name,
        email=email,
        environment_link=link,
        password=password,
    )


def send_customer_password_mail(dexit: DexitSpec, password: str) -> None:
    """
    Send password mail to customer
    """
    config: AppSettings = get_settings()

    domain_name: str = config.dexit.domain_name

    subject = "Your Dexit Environment is Ready"
    content = provisioning_success_mail(
        name=f"{dexit.firstName}_{dexit.lastName}",
        email=dexit.email,
        link=f"https://{dexit.tenant}.{domain_name}",
        password=password,
    )
    send_mail(to_email=dexit.email, subject=subject, content=content, from_name="314e Support")

    log_info(f"Sent provisioning success mail to {dexit.email}")


def reset_keycloak_user_password(dexit: DexitSpec, password: str) -> str:
    """
    reset user temp password in keycloak
    """
    config: AppSettings = get_settings()

    keycloak_admin_client = KeycloakAdminClient(config=config.keycloak)
    realm_name = dexit.tenant

    users = keycloak_admin_client.get_users(query={"email": dexit.email}, realm_name=realm_name)

    if len(users) != 1:
        if len(users) == 0:
            msg = f"OnboardingError: User {dexit.email} not found in realm {realm_name}"
        else:
            msg = f"OnboardingError: Found {len(users)} users with email " f"{dexit.email} in realm {realm_name}"
        raise Exception(msg)

    keycloak_admin_client.set_user_password(user_id=users[0]["id"], password=password, realm_name=realm_name)

    log_info(f"Created temporary password for user {dexit.email} in realm {realm_name}")

    return password


def onboard_success(dexit: DexitSpec) -> None:
    """
    @return:
    """
    password = generate_password(10)
    reset_keycloak_user_password(dexit=dexit, password=password)
    send_customer_password_mail(dexit=dexit, password=password)
    return
