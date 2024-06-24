from app.cli.jeeves import TemplatePath
from app.cli.jeeves.models.jeevesSpec import JeevesSpec
from app.cli.common.keycloakUtils import KeycloakAdminClient
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


def send_customer_password_mail(jeeves: JeevesSpec, password: str) -> None:
    """
    Send password mail to customer
    """
    config: AppSettings = get_settings()

    domain_name: str = config.jeeves.domain_name

    subject = "Your Jeeves Environment is Ready"
    content = provisioning_success_mail(
        name=jeeves.customerDetails.userName,
        email=jeeves.customerDetails.email,
        link=f"https://{jeeves.tenant}.{domain_name}",
        password=password,
    )
    send_mail(to_email=jeeves.customerDetails.email, subject=subject, content=content, from_name="314e Support")


def reset_keycloak_user_password(jeeves: JeevesSpec, password: str) -> str:
    """
    reset user temp password in keycloak
    """
    config: AppSettings = get_settings()

    keycloak_admin_client = KeycloakAdminClient(config=config.keycloak)
    realm_name = jeeves.tenant

    users = keycloak_admin_client.get_users(query={"email": jeeves.customerDetails.email}, realm_name=realm_name)

    if len(users) != 1:
        if len(users) == 0:
            msg = f"OnboardingError: User {jeeves.customerDetails.email} not found in realm {realm_name}"
        else:
            msg = (
                f"OnboardingError: Found {len(users)} users with email "
                f"{jeeves.customerDetails.email} in realm {realm_name}"
            )
        raise Exception(msg)

    keycloak_admin_client.set_user_password(user_id=users[0]["id"], password=password, realm_name=realm_name)

    return password


def onboard_success(jeeves: JeevesSpec) -> None:
    """
    @return:
    """
    password = generate_password(10)
    reset_keycloak_user_password(jeeves=jeeves, password=password)
    send_customer_password_mail(jeeves=jeeves, password=password)
    return
