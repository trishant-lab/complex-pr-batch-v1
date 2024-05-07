import jinja2
import orjson
from loguru import logger

from app.common import generate_password
from app.core.settings import AppSettings, get_settings, ProductConfig, KeycloakSettings
from app.onepasswordutil import OnePasswordUtil
from app.template_env import get_env
from app.temporal.common.keycloakUtils import KeycloakAdminClient
from app.temporal.veritable.utils.common import VeritableSpec, ProductName, OnepasswordVaultName


def create_keycloak_realm(
        veritable: VeritableSpec, config: AppSettings, tenant_url: str, realm_name: str, 
        keycloak_client: KeycloakAdminClient
):
    """
    Create keycloak realm
    """
    jinja_env: jinja2.Environment = get_env(product=ProductName)
    template = jinja_env.get_template("keycloak_realm.json")

    customer_roles = orjson.dumps(veritable.customerRealmRoles).decode("utf-8")

    realm_config = template.render(
        realm_name=realm_name,
        customerRealmRoles=customer_roles,
        tenant=veritable.tenant,
        sendgrid_api_key=config.sendgrid_api_key,
        tenant_url=tenant_url,
    )

    keycloak_client.create_realm(orjson.loads(realm_config))
    
    
def create_tenant_customer_admin_user(veritable: VeritableSpec, keycloak_client: KeycloakAdminClient, realm_name: str):
    customer_password = generate_password(20)

    if veritable.customerUserName in [user['username'] for user in keycloak_client.get_all_users(realm_name)]:
        logger.info(f"User {veritable.customerUserName} already exists in the realm")
        return

    # Create tenant admin customer user
    jinja_env: jinja2.Environment = get_env(product=ProductName)
    template = jinja_env.get_template("keycloak_tenant_customer_admin.json")
    user_config = template.render(
        customerUserName=veritable.customerUserName,
        customerEmail=veritable.customerEmail,
        customerPassword=customer_password,
    )
    keycloak_client.create_user(orjson.loads(user_config), realm_name)


def create_tenant_admin(
        veritable: VeritableSpec, keycloak_client: KeycloakAdminClient, realm_name: str
):
    """
    Create tenant admin user for internal use
    """
    admin_password = generate_password(20)
    username = "admin"

    if username in [user['username'] for user in keycloak_client.get_all_users(realm_name)]:
        logger.info(f"User {username} already exists in the realm")
        return

    jinja_env: jinja2.Environment = get_env(product=ProductName)
    template = jinja_env.get_template("keycloak_tenant_admin.json")
    user_config = template.render(
        username=username,
        password=admin_password,
    )
    keycloak_client.create_user(orjson.loads(user_config), realm_name)

    domain_name: str = get_settings().product_config.get(ProductName).domain_name
    op = OnePasswordUtil(
        tenant=veritable.tenant, server_item=veritable.tenant, vault=OnepasswordVaultName
    )

    op.create_login_item(
        url=f"{veritable.tenant}.{domain_name}", username=username, password=admin_password
    )


async def create_realm_and_users(veritable: VeritableSpec):
    """
    Create keycloak realm and users
    """
    tenant_url = f"{veritable.tenant}.veritable.app" \
        if veritable.environment == "production" else f"{veritable.tenant}.int.veritable.app"

    realm_name = f"veritable_{veritable.tenant}"

    config: AppSettings = get_settings()
    product_config: ProductConfig = get_settings().product_config.get(ProductName)
    keycloak_config: KeycloakSettings = config.keycloak

    keycloak_client = KeycloakAdminClient(keycloak_config)

    # create realm
    create_keycloak_realm(
        veritable=veritable, config=config, tenant_url=tenant_url,
        realm_name=realm_name, keycloak_client=keycloak_client
    )

    # create tenant customer admin user
    create_tenant_customer_admin_user(veritable=veritable, keycloak_client=keycloak_client, realm_name=realm_name)

    # Create tenant admin user for internal use
    create_tenant_admin(
        veritable=veritable, keycloak_client=keycloak_client, realm_name=realm_name
    )
