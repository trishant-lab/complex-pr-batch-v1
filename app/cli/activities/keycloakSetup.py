import jinja2
import orjson

from app.cli.common.keycloakUtils import KeycloakAdminClient, get_keycloak_manager
from app.cli.temporal.core.log import log_info
from app.core.settings import AppSettings, get_settings
from app.template_env import get_env


def create_keycloak_realm(
    tenant: str, config: AppSettings, domain: str, keycloak_client: KeycloakAdminClient, template_path: str
) -> None:
    """
    Create keycloak realm
    """
    jinja_env: jinja2.Environment = get_env(template_path=template_path)
    template = jinja_env.get_template("keycloak_realm.json")

    realm_config = template.render(
        tenant=tenant,
        sendgrid_api_key=config.sendgrid.api_key,
        domain=domain,
    )

    keycloak_client.refresh_token()
    keycloak_client.create_realm(orjson.loads(realm_config), skip_exists=True)

    log_info(f"Keycloak realm {tenant} created successfully")


def create_tenant_customer_admin_user(
    user_details: dict, client_uuid: str, keycloak_client: KeycloakAdminClient, realm_name: str, template_path: str
) -> None:
    """
    Create tenant customer admin user
    """
    # Create tenant admin customer user
    jinja_env: jinja2.Environment = get_env(template_path=template_path)
    template = jinja_env.get_template("keycloak_tenant_customer_admin.json")
    user_config = template.render(
        **user_details,
    )
    keycloak_client.refresh_token()
    keycloak_client.create_user(orjson.loads(user_config), realm_name)

    roles = keycloak_client.get_client_roles(client_id=client_uuid, realm_name=realm_name)

    keycloak_client.assign_client_role(
        client_id=client_uuid,
        user_id=keycloak_client.get_user_id(username=user_details["email"], realm_name=realm_name),
        roles=roles,
        realm_name=realm_name,
    )
    log_info(f"Tenant customer admin user {user_details['firstName']}_{user_details['lastName']} created successfully")


def create_client(
    tenant: str, domain: str, keycloak_client: KeycloakAdminClient, realm_name: str, template_path: str, product: str
) -> None:
    """
    Create keycloak client
    """
    jinja_env: jinja2.Environment = get_env(template_path=template_path)

    template = jinja_env.get_template(f"keycloak_{product.lower()}_client.json")
    client_config = template.render(tenant=tenant, domain=domain)
    keycloak_client.create_client(orjson.loads(client_config), realm_name)

    template = jinja_env.get_template("keycloak_form_auth_client.json")
    form_auth_client_config = template.render(tenant=tenant, domain=domain)
    keycloak_client.create_client(orjson.loads(form_auth_client_config), realm_name)

    log_info(f"Keycloak client {product} created successfully")


def create_client_roles(client_uuid: str, keycloak_client: KeycloakAdminClient, realm_name: str, roles: list) -> None:
    """
    Create keycloak client roles
    """
    for role in roles:
        keycloak_client.create_client_role(client_id=client_uuid, role_config={"name": role}, realm_name=realm_name)

    log_info("Keycloak client roles created successfully")


def create_internal_users(
    client_uuid: str, keycloak_client: KeycloakAdminClient, realm_name: str, template_path: str
) -> None:
    """
    Create internal users
    """
    """
    Create tenant customer admin user
    """
    # Create tenant admin customer user
    jinja_env: jinja2.Environment = get_env(template_path=template_path)
    template = jinja_env.get_template("keycloak_tenant_internal_user.json")

    with open(f"{template_path}/internal_admin_users.json") as f:
        users = orjson.loads(f.read())

    for user in users:
        user_config = template.render(
            username=user["username"],
            email=user["email"],
            firstname=user["firstname"],
            lastname=user["lastname"],
        )
        keycloak_client.refresh_token()
        keycloak_client.create_user(orjson.loads(user_config), realm_name)

        roles = keycloak_client.get_client_roles(client_id=client_uuid, realm_name=realm_name)

        keycloak_client.assign_client_role(
            client_id=client_uuid,
            user_id=keycloak_client.get_user_id(username=user["username"], realm_name=realm_name),
            roles=roles,
            realm_name=realm_name,
        )
        log_info(f"Internal admin user {user['username']} created successfully")

    log_info("Internal admin user created successfully")


async def create_realm_and_users(
    tenant: str, user_details: dict, product: str, roles: list, template_path: str, domain: str
) -> None:
    """
    Create keycloak realm and users
    """
    realm_name = f"{tenant}"

    config: AppSettings = get_settings()

    keycloak_client: KeycloakAdminClient = get_keycloak_manager()

    # create realm
    create_keycloak_realm(
        tenant=tenant, config=config, domain=domain, keycloak_client=keycloak_client, template_path=template_path
    )

    # create client
    create_client(
        tenant=tenant,
        domain=domain,
        keycloak_client=keycloak_client,
        realm_name=realm_name,
        template_path=template_path,
        product=product,
    )

    # get client uuid
    client_uuid = keycloak_client.get_client_id(client=product.lower(), realm_name=realm_name)

    # create client roles
    create_client_roles(client_uuid=client_uuid, keycloak_client=keycloak_client, realm_name=realm_name, roles=roles)

    # create tenant customer admin user
    create_tenant_customer_admin_user(
        user_details=user_details,
        client_uuid=client_uuid,
        keycloak_client=keycloak_client,
        realm_name=realm_name,
        template_path=template_path,
    )

    create_internal_users(
        client_uuid=client_uuid, keycloak_client=keycloak_client, realm_name=realm_name, template_path=template_path
    )
