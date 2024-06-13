import os
import pydash as py_

import jinja2
import orjson

from app.cli.common.keycloakUtils import KeycloakAdminClient, get_keycloak_manager
from app.cli.dexit import TemplatePath
from app.cli.dexit.dexit import DexitSpec
from app.common import generate_password
from app.core.settings import AppSettings, get_settings
from app.onepasswordutil import OnePasswordUtil
from app.template_env import get_env


ROLES = [
    "_standalone-launch",
    "_document-read",
    "_delete-document",
    "_document-indexing",
    "_document-commit",
    "_manage-document-type",
    "_manage-deficiency",
    "_manage-users",
    "_manage-organisation",
    "_manage-document-type",
    "_manage-queues",
    "_manage-subscription",
    "_manage-faxes",
    "_manage-bulk-import",
    "_roi",
    "_reports",
    "_document-review",
]


def create_keycloak_realm(
        dexit: DexitSpec, config: AppSettings, domain: str, keycloak_client: KeycloakAdminClient
):
    """
    Create keycloak realm
    """
    jinja_env: jinja2.Environment = get_env(template_path=TemplatePath)
    template = jinja_env.get_template("keycloak_realm.json")

    realm_config = template.render(
        tenant=dexit.tenant,
        sendgrid_api_key=config.sendgrid_api_key,
        domain=domain,
    )

    keycloak_client.refresh_token()
    keycloak_client.create_realm(orjson.loads(realm_config), skip_exists=False)


def create_client(dexit: DexitSpec, domain: str, keycloak_client: KeycloakAdminClient, realm_name: str):
    """
    Create keycloak client
    """
    jinja_env: jinja2.Environment = get_env(template_path=TemplatePath)
    template = jinja_env.get_template("keycloak_client.json")

    client_config = template.render(
        tenant=dexit.tenant,
        domain=domain,
    )

    keycloak_client.refresh_token()
    keycloak_client.create_client(orjson.loads(client_config), realm_name)


def create_service_account(dexit: DexitSpec, domain: str, keycloak_client: KeycloakAdminClient, realm_name: str):
    """
    Create keycloak service account
    """
    jinja_env: jinja2.Environment = get_env(template_path=TemplatePath)
    template = jinja_env.get_template("keycloak_service_account.json")

    client_secret = generate_password(length=32)

    service_account_config = template.render(
        tenant=dexit.tenant,
        domain=domain,
        secret=client_secret
    )

    keycloak_client.refresh_token()
    keycloak_client.create_client(orjson.loads(service_account_config), realm_name)
    OnePasswordUtil(
        tenant=f"Dexit_Server_{dexit.tenant}",
        server_item="application-config",
        vault="Dexit",
    ).insert_if_not_exists(key="service_account_secret", value=client_secret)


def create_idp_and_flows(dexit: DexitSpec, domain: str, keycloak_client: KeycloakAdminClient, realm_name: str):
    """
    Create keycloak idp and flows
    """
    jinja_env: jinja2.Environment = get_env(template_path=TemplatePath)
    template = jinja_env.get_template("keycloak_idp_and_flows.json")

    client_config = template.render(
        tenant=dexit.tenant,
        domain=domain,
    )
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
                        realm_name=realm_name
                    )


def create_tenant_customer_admin_user(
        dexit: DexitSpec, client_uuid: str, keycloak_client: KeycloakAdminClient, realm_name: str
):
    # Create tenant admin customer user
    jinja_env: jinja2.Environment = get_env(template_path=TemplatePath)
    template = jinja_env.get_template("keycloak_user.json")
    user_config = template.render(
        username=dexit.customerDetails.userName,
        email=dexit.customerDetails.email,
    )
    keycloak_client.refresh_token()
    keycloak_client.create_user(orjson.loads(user_config), realm_name)

    roles = keycloak_client.get_client_roles(client_id=client_uuid, realm_name=realm_name)

    keycloak_client.assign_client_role(
        client_id=client_uuid,
        user_id=keycloak_client.get_user_id(
            username=dexit.customerDetails.userName, realm_name=realm_name
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


async def create_realm_and_users(dexit: DexitSpec):
    """
    Create keycloak realm and users
    """
    environment: str = os.getenv("DEPLOYMENT", "integration").lower()
    domain = "com" if environment == "production" else "tech"

    realm_name = f"{dexit.tenant}"

    config: AppSettings = get_settings()

    keycloak_client: KeycloakAdminClient = get_keycloak_manager()

    # create realm
    create_keycloak_realm(
        dexit=dexit, config=config, domain=domain, keycloak_client=keycloak_client
    )

    # create client
    create_client(dexit=dexit, domain=domain, keycloak_client=keycloak_client, realm_name=realm_name)

    # create service account
    create_service_account(dexit=dexit, domain=domain, keycloak_client=keycloak_client, realm_name=realm_name)

    # create idp and flows
    create_idp_and_flows(dexit=dexit, domain=domain, keycloak_client=keycloak_client, realm_name=realm_name)

    client_uuid = keycloak_client.get_client_id(client="dexit", realm_name=realm_name)

    # create client roles
    create_client_roles(client_uuid=client_uuid, keycloak_client=keycloak_client, realm_name=realm_name)

    # create tenant customer admin user
    create_tenant_customer_admin_user(
        client_uuid=client_uuid, dexit=dexit, keycloak_client=keycloak_client, realm_name=realm_name
    )
