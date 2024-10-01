import os
import pydash as py_

import jinja2
import orjson
from app.cli.common.keycloakUtils import KeycloakAdminClient, get_keycloak_manager
from app.cli.penknife import TemplatePath
from app.cli.penknife.models.penknifespec import PenknifeSpec
from app.cli.temporal.core.log import log_info
from app.common import generate_password
from app.core.settings import AppSettings, get_settings
from app.onepasswordutil import OnePasswordUtil
from app.template_env import get_env
import asyncio

ROLES = [
    "_broadcast-mail",
    "_bulk-account",
    "_write-account",
    "_view-account",
    "_delete-account",
    "_bulk-candidate",
    "_write-candidate",
    "_view-candidate",
    "_delete-candidate",
    "_bulk-contact",
    "_write-contact",
    "_view-contact",
    "_delete-contact",
    "_view-jobs",
    "_write-jobs",
    "_bulk-jobs",
    "_delete-jobs",
    "_view-application",
    "_write-application",
    "_delete-application",
    "_view-opportunity",
    "_write-opportunity",
    "_bulk-opportunity",
    "_delete-opportunity",
    "_view-placement",
    "_write-placement",
    "_delete-placement",
    "_bulk-placement",
    "_view-staticlist",
    "_write-staticlist",
    "_delete-staticlist",
    "_bulk-staticlist",
    "_export-account",
    "_export-candidate",
    "_export-contact",
    "_export-placement",
    "_export-jobs",
    "_export-application",
    "_export-opportunity",
    "_manage-activities",
    "_manage-company",
    "_penknife-admin",
    "_workspace-admin",
    "_manage-entities",
    "_manage-forms",
    "_manage-email-settings",
    "_manage-fields",
    "_manage-integrations",
    "_manage-listofvalues",
    "_manage-pipelines",
    "_manage-teams",
    "_send-mail",
    "_send-bulk-mail",
    "_view-imports",
    "_view-insights",
    "_manage-assessment-cards",
    "_manage-locations-departments",
    "_manage-screening-questionnaire",
    "_manage-career-portal",
    "_manage-workflows",
    "_manage-saved-search (edited) ",
]

DEFAULT_CLIENT_IDS = set([
    "account",
    "account-console",
    "admin-cli",
    "broker",
    "realm-management",
    "security-admin-console",
    "auth"
])


def create_keycloak_realm(
    penknife: PenknifeSpec,
    config: AppSettings,
    domain: str,
    keycloak_client: KeycloakAdminClient,
) -> None:
    """
    Create keycloak realm
    """
    jinja_env: jinja2.Environment = get_env(template_path=TemplatePath)
    template = jinja_env.get_template("keycloak_realm.json")

    realm_config = template.render(
        tenant=penknife.tenant, sendgrid_api_key=config.sendgrid.api_key
    )

    keycloak_client.refresh_token()
    keycloak_client.create_realm(orjson.loads(realm_config), skip_exists=True)

    log_info(f"Keycloak realm {penknife.tenant} created successfully")


def create_tenant_customer_admin_user(
    penknife: PenknifeSpec,
    client_uuid: str,
    keycloak_client: KeycloakAdminClient,
    realm_name: str,
) -> None:
    """
    Create tenant customer admin user
    """
    # Create tenant admin customer user
    jinja_env: jinja2.Environment = get_env(template_path=TemplatePath)
    template = jinja_env.get_template("keycloak_user.json")
    user_config = template.render(
        username=penknife.email,
        email=penknife.email,
        firstname=penknife.firstName,
        lastname=penknife.lastName,
    )
    keycloak_client.refresh_token()
    keycloak_client.create_user(orjson.loads(user_config), realm_name)

    roles = keycloak_client.get_client_roles(
        client_id=client_uuid, realm_name=realm_name
    )

    keycloak_client.assign_client_role(
        client_id=client_uuid,
        user_id=keycloak_client.get_user_id(
            username=penknife.email, realm_name=realm_name
        ),
        roles=roles,
        realm_name=realm_name,
    )
    log_info(f"Tenant customer admin user {penknife.email} created successfully")


def create_client(
    penknife: PenknifeSpec,
    domain: str,
    keycloak_client: KeycloakAdminClient,
    realm_name: str,
) -> None:
    """
    Create keycloak client
    """
    jinja_env: jinja2.Environment = get_env(template_path=TemplatePath)

    client_template = jinja_env.get_template("keycloak_client.json")
    client_config = client_template.render(tenant=penknife.tenant, domain=domain)

    keycloak_client.refresh_token()
    keycloak_client.create_client(orjson.loads(client_config), realm_name)
    log_info("Keycloak client penknife created successfully")


    all_clients = keycloak_client.get_all_clients(realm_name=realm_name)
    auth_exists = any(True for client in all_clients if client.get("clientId") == "auth")

    # If auth client does not exist, then create it.
    if not auth_exists:
        auth_client_template = jinja_env.get_template("keycloak_auth_client.json")
        auth_credential = generate_password(length=32)
        OnePasswordUtil(
            tenant=f"PENKNIFE_{penknife.tenant}",
            server_item="application-config",
            vault="Penknife",
        ).create_or_replace("auth_credential", auth_credential)

        auth_client_config = auth_client_template.render(tenant=penknife.tenant, domain=domain, auth_credential=auth_credential)
        keycloak_client.refresh_token()
        keycloak_client.create_client(orjson.loads(auth_client_config), realm_name)

        log_info("Keycloak auth client for penknife created successfully")


def create_idp_and_flows(
    penknife: PenknifeSpec,
    domain: str,
    keycloak_client: KeycloakAdminClient,
    realm_name: str,
) -> None:
    """
    Create keycloak idp and flows
    """
    jinja_env: jinja2.Environment = get_env(template_path=TemplatePath)
    template = jinja_env.get_template("keycloak_idp_and_flows.json")

    # googleidp = ""
    client_config = template.render(googleclientid="", googlesecret="")

    client_config = orjson.loads(client_config)
    flow_configs = client_config["authenticationFlows"]
    idp_configs = client_config["identityProviders"]
    idp_mapper_configs = client_config["identityProviderMappers"]

    keycloak_client.refresh_token()
    for flow_config in flow_configs:
        keycloak_client.create_authentication_flow(flow_config, realm_name)

    identity_providers = keycloak_client.get_identity_providers(realm_name=realm_name)
    for idp_config in idp_configs:
        if not py_.find(identity_providers, {"alias": idp_config["alias"]}):
            keycloak_client.create_identity_provider(idp_config, realm_name)
            for idp_mapper_config in idp_mapper_configs:
                if idp_mapper_config["identityProviderAlias"] == idp_config["alias"]:
                    keycloak_client.add_mapper_to_idp(
                        idp_alias=idp_mapper_config["identityProviderAlias"],
                        mapper_config=idp_mapper_config,
                        realm_name=realm_name,
                    )

    log_info(f"Keycloak idp and flows {penknife.tenant} created successfully.")


def create_client_roles(
    client_uuid: str, keycloak_client: KeycloakAdminClient, realm_name: str
) -> None:
    """
    Create keycloak client roles
    """
    for role in ROLES:
        keycloak_client.create_client_role(
            client_id=client_uuid, role_config={"name": role}, realm_name=realm_name
        )

    log_info("Keycloak client roles created successfully")


async def create_realm_and_users(penknife: PenknifeSpec) -> None:
    """
    Create keycloak realm and users
    """
    environment: str = os.getenv("DEPLOYMENT", "integration").lower()
    domain = "com" if environment == "production" else "tech"

    realm_name = f"{penknife.tenant}"

    config: AppSettings = get_settings()

    keycloak_client: KeycloakAdminClient = get_keycloak_manager()

    # create realm
    create_keycloak_realm(
        penknife=penknife, config=config, domain=domain, keycloak_client=keycloak_client
    )

    # create client
    create_client(
        penknife=penknife,
        domain=domain,
        keycloak_client=keycloak_client,
        realm_name=realm_name,
    )

    # create idp and flows
    create_idp_and_flows(
        penknife=penknife,
        domain=domain,
        keycloak_client=keycloak_client,
        realm_name=realm_name,
    )

    client_uuid = keycloak_client.get_client_id(
        client="penknife", realm_name=realm_name
    )

    # create client roles
    create_client_roles(
        client_uuid=client_uuid, keycloak_client=keycloak_client, realm_name=realm_name
    )

    # create tenant customer admin user
    create_tenant_customer_admin_user(
        client_uuid=client_uuid,
        penknife=penknife,
        keycloak_client=keycloak_client,
        realm_name=realm_name,
    )

async def delete_clients_and_realms(penknife: PenknifeSpec) -> None:
    """
    Delete keycloak clients and realm
    """

    realm_name = f"{penknife.tenant}"

    keycloak_client: KeycloakAdminClient = get_keycloak_manager()

    all_clients = keycloak_client.get_all_clients(realm_name=realm_name)
    other_client_exists = any(True for client in all_clients if client.get("clientId") and client.get("clientId") not in DEFAULT_CLIENT_IDS)

    # If there are other client present, delete only the needed client otherwise delete the tenant
    if other_client_exists:
        keycloak_client.delete_client("penknife")
        log_info("Keycloak client penknife deleted successfully")
    else:
        keycloak_client.delete_realm(realm_name=realm_name)
        log_info(f"Keycloak realm {realm_name} deleted successfully")

async def get_keycloak_user_id(penknife: PenknifeSpec) -> str:
    """
    Fetch keycloak user id corresponding to tenant email
    """

    realm_name = f"{penknife.tenant}"

    keycloak_client: KeycloakAdminClient = get_keycloak_manager()

    return keycloak_client.get_user_id(realm_name=realm_name, username=penknife.email)
