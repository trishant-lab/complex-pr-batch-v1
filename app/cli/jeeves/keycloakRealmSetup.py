import os

import jinja2
import orjson

from app.cli.common.keycloakUtils import KeycloakAdminClient, get_keycloak_manager
from app.cli.jeeves import TemplatePath
from app.cli.jeeves.common import JeevesSpec
from app.core.settings import AppSettings, get_settings
from app.template_env import get_env


ROLES = [
    "_access-manage-todos",
    "_access-manage-alerts",
    "_access-settings",
    "_allow-delete-assets",
    "_allow-add-edit-assets",
    "_access-reports",
    "_allow-view-assets",
    "_JEEVESALL",
    "_allow-conversion-tools",
    "_developer",
    "_access-screen-recorder",
    "_allow-standalone-launch",
    "_allow-publish-assets",
    "_can-report-issues",
    "_access-chatbot",
    "_can-manage-activities",
    "_allow-add-edit-courses",
    "_allow-delete-courses",
    "_allow-enroll-courses",
    "_allow-view-all-courses",
]


def create_keycloak_realm(
        jeeves: JeevesSpec, config: AppSettings, domain: str, keycloak_client: KeycloakAdminClient
):
    """
    Create keycloak realm
    """
    jinja_env: jinja2.Environment = get_env(template_path=TemplatePath)
    template = jinja_env.get_template("keycloak_realm.json")

    realm_config = template.render(
        tenant=jeeves.tenant,
        sendgrid_api_key=config.sendgrid_api_key,
        domain=domain,
    )

    keycloak_client.refresh_token()
    keycloak_client.create_realm(orjson.loads(realm_config))


def create_tenant_customer_admin_user(
        jeeves: JeevesSpec, client_uuid: str, keycloak_client: KeycloakAdminClient, realm_name: str
):
    # Create tenant admin customer user
    jinja_env: jinja2.Environment = get_env(template_path=TemplatePath)
    template = jinja_env.get_template("keycloak_tenant_customer_admin.json")
    user_config = template.render(
        username=jeeves.customerDetails.customerUserName,
        email=jeeves.customerDetails.customerEmail,
    )
    keycloak_client.refresh_token()
    keycloak_client.create_user(orjson.loads(user_config), realm_name)

    roles = keycloak_client.get_client_roles(client_id=client_uuid, realm_name=realm_name)

    keycloak_client.assign_client_role(
        client_id=client_uuid,
        user_id=keycloak_client.get_user_id(
            username=jeeves.customerDetails.customerUserName, realm_name=realm_name
        ),
        roles=roles,
        realm_name=realm_name,

    )


def create_client_roles(client_uuid: str, keycloak_client: KeycloakAdminClient, realm_name: str):
    """
    Create keycloak client roles
    """
    for role in ROLES:
        keycloak_client.create_client_role(
            client_id=client_uuid, role_config={"name": role}, realm_name=realm_name
        )


async def create_realm_and_users(jeeves: JeevesSpec):
    """
    Create keycloak realm and users
    """
    environment: str = os.getenv("DEPLOYMENT", "integration").lower()
    domain = "com" if environment == "production" else "tech"

    realm_name = f"{jeeves.tenant}"

    config: AppSettings = get_settings()

    keycloak_client: KeycloakAdminClient = get_keycloak_manager()

    # create realm
    create_keycloak_realm(
        jeeves=jeeves, config=config, domain=domain, keycloak_client=keycloak_client
    )

    client_uuid = keycloak_client.get_client_id(client="jeeves", realm_name=realm_name)

    # create client roles
    create_client_roles(client_uuid=client_uuid, keycloak_client=keycloak_client, realm_name=realm_name)

    # create tenant customer admin user
    create_tenant_customer_admin_user(
        client_uuid=client_uuid, jeeves=jeeves, keycloak_client=keycloak_client, realm_name=realm_name
    )
