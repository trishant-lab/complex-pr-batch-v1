import os

import jinja2
import orjson

from app.cli.common.keycloakUtils import KeycloakAdminClient, get_keycloak_manager
from app.cli.veritable import TemplatePath
from app.cli.veritable.models.veritableSpec import VeritableSpec
from app.core.settings import AppSettings, get_settings
from app.template_env import get_env


def create_keycloak_realm(
    veritable: VeritableSpec,
    config: AppSettings,
    tenant_url: str,
    realm_name: str,
    keycloak_client: KeycloakAdminClient,
) -> None:
    """
    Create keycloak realm
    """
    jinja_env: jinja2.Environment = get_env(template_path=TemplatePath)
    template = jinja_env.get_template("keycloak_realm.json")

    customer_realm_roles = ["VT_CUSTOMER_ADMIN"]

    customer_roles = orjson.dumps(customer_realm_roles).decode("utf-8")

    realm_config = template.render(
        realm_name=realm_name,
        customerRealmRoles=customer_roles,
        tenant=veritable.tenant,
        sendgrid_api_key=config.sendgrid_api_key,
        tenant_url=tenant_url,
    )

    keycloak_client.refresh_token()
    keycloak_client.create_realm(orjson.loads(realm_config))


def create_tenant_customer_admin_user(
    veritable: VeritableSpec, keycloak_client: KeycloakAdminClient, realm_name: str
) -> None:
    """
    Create tenant customer admin user
    """
    # Create tenant admin customer user
    jinja_env: jinja2.Environment = get_env(template_path=TemplatePath)
    template = jinja_env.get_template("keycloak_tenant_customer_admin.json")
    user_config = template.render(
        customerUserName=veritable.customerDetails.userName,
        customerEmail=veritable.customerDetails.email,
    )
    keycloak_client.refresh_token()
    keycloak_client.create_user(orjson.loads(user_config), realm_name)


def create_tenant_admin(keycloak_client: KeycloakAdminClient, realm_name: str) -> None:
    """
    Create tenant admin user for internal use
    """
    username = "admin"

    jinja_env: jinja2.Environment = get_env(template_path=TemplatePath)
    template = jinja_env.get_template("keycloak_tenant_admin.json")
    user_config = template.render(
        username=username,
    )
    keycloak_client.refresh_token()
    keycloak_client.create_user(orjson.loads(user_config), realm_name)


async def create_realm_and_users(veritable: VeritableSpec) -> None:
    """
    Create keycloak realm and users
    """
    environment: str = os.getenv("DEPLOYMENT", "integration").lower()
    tenant_url = (
        f"{veritable.tenant}.veritable.app" if environment == "production" else f"{veritable.tenant}.int.veritable.app"
    )

    realm_name = f"veritable_{veritable.tenant}"

    config: AppSettings = get_settings()

    keycloak_client: KeycloakAdminClient = get_keycloak_manager()

    # create realm
    create_keycloak_realm(
        veritable=veritable,
        config=config,
        tenant_url=tenant_url,
        realm_name=realm_name,
        keycloak_client=keycloak_client,
    )

    # create tenant customer admin user
    create_tenant_customer_admin_user(veritable=veritable, keycloak_client=keycloak_client, realm_name=realm_name)

    # Create tenant admin user for internal use
    create_tenant_admin(keycloak_client=keycloak_client, realm_name=realm_name)
