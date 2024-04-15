from dataclasses import dataclass

import jinja2
import orjson
from loguru import logger
from temporalio import activity

from app.common import generate_password
from app.core.settings import KeycloakSettings, get_settings, ProductConfig
from app.temporalworkflows.common.keyclaokrealmsetup.keycloakutils import KeycloakAdminClient
from app.temporalworkflows.onepasswordutil import OnePasswordUtil
from app.temporalworkflows.template_env import get_env


def check_keycloak_realm_exists(keycloak_client: KeycloakAdminClient, realm_name: str) -> bool:
    """
    Check if keycloak realm exists
    """
    realms = [row["realm"] for row in keycloak_client.get_all_realms()]
    return realm_name in realms


def create_tenant_admin_customer_user(
        keycloak_client: KeycloakAdminClient,
        jinja_env: jinja2.Environment,
        customer_details: dict,
        realm_name: str
) -> None:
    """
    Create tenant admin customer user
    """
    template = jinja_env.get_template("keycloak_tenant_customer_admin.json")
    user_config = template.render(
        customerUserName=customer_details["customer_username"],
        customerEmail=customer_details["customer_email"],
        customerPassword=customer_details["customer_password"],
    )
    keycloak_client.create_user(orjson.loads(user_config), realm_name)


def create_tenant_admin(
        keycloak_client: KeycloakAdminClient,
        jinja_env: jinja2.Environment,
        admin_details: dict,
        realm_name: str
) -> None:
    """
    Create tenant admin
    """
    template = jinja_env.get_template("keycloak_tenant_admin.json")
    user_config = template.render(
        username=admin_details.get("username", "admin"),
        password=admin_details.get("password"),
    )
    keycloak_client.create_user(orjson.loads(user_config), realm_name)


@dataclass
class CreateKeycloakRealmActivityInput:
    realm_name: str
    product: str
    customerRealmRoles: list[str]
    tenant: str
    domain_org: str
    customer_username: str
    customer_email: str
    admin_user: str
    admin_email: str


@activity.defn(name="create_keycloak_realm_activity")
async def create_keycloak_realm_activity(activity_input: CreateKeycloakRealmActivityInput) -> None:
    """
    :return:
    """
    keycloak_config: KeycloakSettings = get_settings().keycloak
    keycloak_client = KeycloakAdminClient(keycloak_config)
    sendgrid_api_key = ""

    product_config: ProductConfig = get_settings().product_config.get(activity_input.product)

    if check_keycloak_realm_exists(keycloak_client=keycloak_client, realm_name=activity_input.realm_name):
        logger.info("Realm already exists")
        return

    logger.info("Starting keycloak realm creation")
    jinja_env: jinja2.Environment = get_env(activity_input.product)
    template = jinja_env.get_template("keycloak_realm.json")

    customer_roles = orjson.dumps(activity_input.customerRealmRoles).decode("utf-8")

    realm_config = template.render(
        realm_name=activity_input.realm_name,
        customerRealmRoles=customer_roles,
        tenant=activity_input.tenant,
        sendgrid_api_key=sendgrid_api_key,
        domain_org=activity_input.domain_org,
    )

    keycloak_client.create_realm(orjson.loads(realm_config))

    logger.info("Keycloak realm created successfully")

    customer_password = generate_password(20)

    # Create tenant admin customer user
    custom_details = {
        "customer_username": activity_input.customer_username,
        "customer_email": activity_input.customer_email,
        "customer_password": customer_password
    }
    create_tenant_admin_customer_user(
        keycloak_client=keycloak_client,
        jinja_env=jinja_env,
        customer_details=custom_details,
        realm_name=activity_input.realm_name
    )
    logger.info("Tenant admin customer user created successfully")

    admin_password = generate_password(20)

    # Create tenant admin user for internal use
    admin_details = {
        "username": activity_input.admin_user,
        "email": activity_input.admin_email,
        "password": admin_password
    }
    create_tenant_admin(
        keycloak_client=keycloak_client,
        jinja_env=jinja_env,
        admin_details=admin_details,
        realm_name=activity_input.realm_name
    )
    logger.info("Tenant admin user created successfully")

    # Create 1Password login item
    domain_name: str = get_settings().product_config.get(activity_input.product).domain_name
    op = OnePasswordUtil(
        tenant=activity_input.tenant, server_item=activity_input.tenant, vault=product_config.vault_name
    )

    op.create_login_item(
        url=f"{activity_input.tenant}.{domain_name}", username=activity_input.admin_user, password=admin_password
    )
