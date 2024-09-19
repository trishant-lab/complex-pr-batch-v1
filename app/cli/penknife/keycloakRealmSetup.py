

import jinja2
import orjson
from app.cli.common.keycloakUtils import KeycloakAdminClient
from app.cli.penknife import TemplatePath
from app.cli.penknife.models.penknifespec import PenknifeSpec
from app.cli.temporal.core.log import log_info
from app.core.settings import AppSettings
from app.template_env import get_env


ROLES = [
    ""
]

def create_keycloak_realm(
    penknife: PenknifeSpec, config: AppSettings, domain: str, keycloak_client: KeycloakAdminClient
) -> None:
    """
    Create keycloak realm
    """
    jinja_env: jinja2.Environment = get_env(template_path=TemplatePath)
    template = jinja_env.get_template("keycloak_realm.json")

    realm_config = template.render(
        tenant=penknife.tenant
    )

    keycloak_client.refresh_token()
    keycloak_client.create_realm(orjson.loads(realm_config), skip_exists=True)

    log_info(f"Keycloak realm {penknife.tenant} created successfully")

def create_tenant_customer_admin_user(
    penknife: PenknifeSpec, client_uuid: str, keycloak_client: KeycloakAdminClient, realm_name: str
) -> None:
    """
    Create tenant customer admin user
    """
    # Create tenant admin customer user
    jinja_env: jinja2.Environment = get_env(template_path=TemplatePath)
    template = jinja_env.get_template("keycloak_tenant_customer_admin.json")
    user_config = template.render(
        username=f"{penknife.firstName}_{penknife.lastName}",
        email=penknife.email,
    )
    keycloak_client.refresh_token()
    keycloak_client.create_user(orjson.loads(user_config), realm_name)

    roles = keycloak_client.get_client_roles(client_id=client_uuid, realm_name=realm_name)

    keycloak_client.assign_client_role(
        client_id=client_uuid,
        user_id=keycloak_client.get_user_id(username=f"{penknife.firstName}_{penknife.lastName}", realm_name=realm_name),
        roles=roles,
        realm_name=realm_name,
    )
    log_info(f"Tenant customer admin user {penknife.firstName}_{penknife.lastName} created successfully")

def create_client(penknife: PenknifeSpec, domain: str, keycloak_client: KeycloakAdminClient, realm_name: str) -> None:
    """
    Create keycloak client
    """
    jinja_env: jinja2.Environment = get_env(template_path=TemplatePath)

    template = jinja_env.get_template("keycloak_penknife_client.json")
    client_config = template.render(tenant=penknife.tenant, domain=domain)
    keycloak_client.create_client(orjson.loads(client_config), realm_name)

    template = jinja_env.get_template("keycloak_form_auth_client.json")
    form_auth_client_config = template.render(tenant=penknife.tenant, domain=domain)
    keycloak_client.create_client(orjson.loads(form_auth_client_config), realm_name)

    log_info("Keycloak client penknife created successfully")

def create_idp_and_flows(penknife: PenknifeSpec, domain: str, keycloak_client: KeycloakAdminClient, realm_name: str) -> None:
    """
    Create keycloak idp and flows
    """
    jinja_env: jinja2.Environment = get_env(template_path=TemplatePath)
    template = jinja_env.get_template("keycloak_idp_and_flows.json")

    googleidp = ""
    



def create_client_roles(client_uuid: str, keycloak_client: KeycloakAdminClient, realm_name: str) -> None:
    """
    Create keycloak client roles
    """
    for role in ROLES:
        keycloak_client.create_client_role(client_id=client_uuid, role_config={"name": role}, realm_name=realm_name)

    log_info("Keycloak client roles created successfully")
