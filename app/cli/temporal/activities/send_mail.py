import os
from datetime import timedelta
from tempfile import TemporaryDirectory

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.keycloak_utils import KeycloakAdminClient, get_keycloak_manager
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
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
        template_env.variable_start_string = "{{"
        template_env.variable_end_string = "}}"
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
            "get_email_template_by_product.sql", product=product, template_name="AfterProvisioning"
        )
        response = dict(response)
    except Exception as e:
        log_error(f"Error fetching template: {e}")
        raise RuntimeError("Error fetching email template")

    subject = response["subject"]
    content = await provisioning_success_mail(
        name=f"{user_details.get('firstName')} {user_details.get('lastName')}",
        email=user_details.get("email"),
        link=f"https://{tenant}.{domain_name}",
        password=password,
        email_template=response["template"],
    )
    await send_mail(
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
            msg = f"OnboardingError: Found {len(users)} users with email {email} in realm {realm_name}"
        raise RuntimeError(msg)

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


async def send_before_provisioning_mail(user_details: dict, product: str, from_name: str, email_from: str) -> None:
    """
    Send mail to customer before provisioning
    """
    db: DBManager = await get_db_manager()

    # get template
    try:
        response = await db.fetch_one(
            "get_email_template_by_product.sql", product=product, template_name="BeforeProvisioning"
        )
        response = dict(response)
    except Exception as e:
        log_error(f"Error fetching template: {e}")
        raise RuntimeError("Error fetching email template")

    subject = response["subject"]

    with TemporaryDirectory() as temp_dir:
        with open(f"{temp_dir}/before_provisioning_mail.html", "w") as f:
            f.write(response["template"])

        template_env = get_env(template_path=temp_dir)
        template_env.variable_start_string = "{{"
        template_env.variable_end_string = "}}"
        template = template_env.get_template("before_provisioning_mail.html")
        content = template.render(
            user_name=f"{user_details.get('firstName')} {user_details.get('lastName')}",
        )
        if product == "jeeves" or product == "pricedx":
            theme_template_env = get_env(
                template_path=os.path.join(
                    os.path.dirname(os.path.realpath(__file__)),
                    f"../{product}/templates",
                )
            )
            theme_template_env.variable_start_string = "{{"
            theme_template_env.variable_end_string = "}}"
            template = theme_template_env.get_template("theme.html")
            content = template.render(body=content)

    await send_mail(
        to_email=user_details.get("email"),
        subject=subject,
        content=content,
        from_name=from_name,
        email_from=email_from,
    )
    log_info(f"Sent before provisioning mail to {user_details.get('email')}")


class SendBeforeProvisioningMailActivityModel(LaunchpadCLIBaseModel):
    """
    SendBeforeProvisioningMailActivityModel
    """

    user_details: dict
    product: str
    from_name: str
    email_from: str


class JeevesSendAfterProvisioningMailActivityModel(LaunchpadCLIBaseModel):
    """
    JeevesSendAfterProvisioningMailActivityModel
    """

    realm_name: str
    client_id: str


class SendBeforeProvisioningMailActivity(Activity):
    """
    SendBeforeProvisioningMailActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=180)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="SendBeforeProvisioningMailActivity")
    async def defn(activity_input: SendBeforeProvisioningMailActivityModel) -> None:
        """
        Callable for the activity
        """
        await send_before_provisioning_mail(
            user_details=activity_input.user_details,
            product=activity_input.product,
            from_name=activity_input.from_name,
            email_from=activity_input.email_from,
        )


class SendAfterProvisioningMailActivityModel(LaunchpadCLIBaseModel):
    """
    SendAfterProvisioningMailActivityModel
    """

    tenant: str
    realm_name: str
    user_details: dict
    domain_name: str
    product: str
    from_name: str
    email_from: str


class SendAfterProvisioningMailActivity(Activity):
    """
    SendAfterProvisioningMailActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="SendAfterProvisioningMailActivity")
    async def defn(activity_input: SendAfterProvisioningMailActivityModel) -> None:
        """
        Callable for the activity
        """
        await send_provisioning_mail(
            tenant=activity_input.tenant,
            realm_name=activity_input.realm_name,
            user_details=activity_input.user_details,
            domain_name=activity_input.domain_name,
            product=activity_input.product,
            from_name=activity_input.from_name,
            email_from=activity_input.email_from,
        )


class JeevesSendAfterProvisioningMailActivity(Activity):
    """
    SendAfterProvisioningMailActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="JeevesSendAfterProvisioningMailActivity")
    async def defn(activity_input: JeevesSendAfterProvisioningMailActivityModel) -> None:
        """
        Callable for the activity
        """
        kc_client = get_keycloak_manager()
        realm_users = kc_client.get_users(realm_name=activity_input.realm_name)
        [
            kc_client.send_reset_password_link(
                user.get("id"), realm_name=activity_input.realm_name, client_id=activity_input.client_id
            )
            for user in realm_users
            if user and user.get("id")
        ]
