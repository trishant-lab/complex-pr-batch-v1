from datetime import timedelta

import jinja2
from pydash import py_
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.keycloak_utils import KeycloakAdminClient, get_keycloak_manager
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_error, log_info
from app.core.ijson import ijson_loads
from app.core.settings import AppSettings, get_settings
from app.one_password_util import OnePasswordUtil
from app.template_env import get_env


def template_render(
    template_path: str,
    template_name: str,
    template_payload: dict | None = None,
) -> str:
    """
    Render template
    """
    jinja_env: jinja2.Environment = get_env(template_path=template_path)
    template = jinja_env.get_template(template_name)
    if template_payload and "jinja_env.autoescape" in template_payload:
        jinja_env.autoescape = template_payload["jinja_env.autoescape"]
        del template_payload["jinja_env.autoescape"]
    return template.render(**(template_payload if template_payload else {}))


def get_ehr_based_idp_template(ehr: str) -> str:
    """
    Return IDP template based on EHR
    """
    match ehr.lower():
        case "cerner":
            return "keycloak_cerner_ehr_idp_flows.json"
        case "epic":
            return "keycloak_epic_ehr_idp_flows.json"
        case _:
            return "keycloak_idp_and_flows.json"


def create_keycloak_realm(
    realm_name: str,
    domain: str,
    template_path: str,
    template_name: str,
    installer_secret: str | None = None,
    template_payload: dict | None = None,
) -> None:
    """
    Create keycloak realm
    """
    config: AppSettings = get_settings()

    realm_config = template_render(
        template_path=template_path,
        template_name=template_name,
        template_payload={
            "tenant": realm_name,
            "sendgrid_api_key": config.sendgrid.api_key,
            "domain": domain,
            "installer_secret": installer_secret,
            **(template_payload if template_payload else {}),
        },
    )

    keycloak_client: KeycloakAdminClient = get_keycloak_manager()
    keycloak_client.create_realm(ijson_loads(realm_config), skip_exists=True)


def create_keycloak_client(
    tenant: str,
    realm_name: str,
    domain: str,
    template_path: str,
    template_name: str,
    auth_credential: str | None = None,
    template_payload: dict | None = None,
) -> None:
    """
    Create keycloak client
    """
    client_config = template_render(
        template_path=template_path,
        template_name=template_name,
        template_payload={
            "tenant": tenant,
            "domain": domain,
            "auth_credential": auth_credential,
            **(template_payload if template_payload else {}),
        },
    )

    keycloak_client: KeycloakAdminClient = get_keycloak_manager()
    keycloak_client.create_client(ijson_loads(client_config), realm_name)


def create_keycloak_service_account(
    tenant: str,
    realm_name: str,
    domain: str,
    template_path: str,
    template_name: str,
    secret: str,
) -> None:
    """
    Create keycloak service account
    """
    service_account_config = template_render(
        template_path=template_path,
        template_name=template_name,
        template_payload={
            "tenant": tenant,
            "domain": domain,
            "secret": secret,
        },
    )

    keycloak_client: KeycloakAdminClient = get_keycloak_manager()
    keycloak_client.create_client(ijson_loads(service_account_config), realm_name)


def create_client_roles(
    client_name: str,
    realm_name: str,
    roles: list[str],
) -> None:
    """
    Create client roles
    """
    keycloak_client: KeycloakAdminClient = get_keycloak_manager()
    client_uuid = keycloak_client.get_client_id(client=client_name, realm_name=realm_name)

    for role in roles:
        keycloak_client.create_client_role(client_id=client_uuid, role_config={"name": role}, realm_name=realm_name)


def create_tenant_customer_admin_user(
    realm_name: str,
    client_name: str,
    username: str,
    email: str,
    firstname: str,
    lastname: str,
    template_path: str,
    template_name: str,
    group_path: str | None,
    roles: list[str] | None = None,
) -> None:
    """
    Create tenant customer admin user
    """
    keycloak_client: KeycloakAdminClient = get_keycloak_manager()

    # First check if realm exists
    if keycloak_client.get_realm(realm_name):
        log_info(f"Realm {realm_name} already exists")
        return

    user_config = template_render(
        template_path=template_path,
        template_name=template_name,
        template_payload={
            "username": username,
            "email": email,
            "firstname": firstname,
            "lastname": lastname,
        },
    )

    keycloak_client.create_user(ijson_loads(user_config), realm_name)

    client_uuid = keycloak_client.get_client_id(client=client_name, realm_name=realm_name)

    client_roles = keycloak_client.get_client_roles(client_id=client_uuid, realm_name=realm_name)

    user_id = keycloak_client.get_user_id(username=username, realm_name=realm_name)
    keycloak_client.assign_client_role(
        client_id=client_uuid,
        user_id=user_id,
        roles=(
            [{"id": role.get("id"), "name": role.get("name")} for role in client_roles if role.get("name") in roles]
            if roles
            else client_roles
        ),
        realm_name=realm_name,
    )
    if group_path:
        keycloak_client.assign_group(
            user_id=user_id,
            realm_name=realm_name,
            group_id=keycloak_client.get_group_id_by_path(realm_name=realm_name, path=group_path),
        )


def create_internal_users(
    realm_name: str,
    client_name: str,
    template_path: str,
    template_name: str,
    users: list[dict],
    group_path: str | None,
    roles: list[str] | None = None,
) -> None:
    """
    Create internal users
    """
    keycloak_client: KeycloakAdminClient = get_keycloak_manager()

    client_id = keycloak_client.get_client_id(client=client_name, realm_name=realm_name)

    client_roles = keycloak_client.get_client_roles(client_id=client_id, realm_name=realm_name)

    for user in users:
        user_config = template_render(
            template_path=template_path,
            template_name=template_name,
            template_payload={
                "username": user["username"],
                "email": user["email"],
                "firstname": user["firstname"],
                "lastname": user["lastname"],
            },
        )

        keycloak_client.create_user(ijson_loads(user_config), realm_name)

        log_info(f"Keycloak internal user {user['username']} created successfully")
        user_id = keycloak_client.get_user_id(username=user["username"], realm_name=realm_name)

        keycloak_client.assign_client_role(
            client_id=client_id,
            user_id=user_id,
            roles=(
                [{"id": role.get("id"), "name": role.get("name")} for role in client_roles if role.get("name") in roles]
                if roles
                else client_roles
            ),
            realm_name=realm_name,
        )
        if group_path:
            keycloak_client.assign_group(
                realm_name=realm_name,
                user_id=user_id,
                group_id=keycloak_client.get_group_id_by_path(realm_name=realm_name, path=group_path),
            )


def create_keycloak_group(
    realm_name: str,
    client_name: str,
    template_path: str,
    template_name: str,
) -> None:
    """
    Create keycloak group
    """
    keycloak_client: KeycloakAdminClient = get_keycloak_manager()

    client_id = keycloak_client.get_client_id(client=client_name, realm_name=realm_name)

    with open(f"{template_path}/{template_name}") as f:
        user_groups = ijson_loads(f.read())

    for group_name, roles in user_groups.items():
        keycloak_client.create_group(payload={"name": group_name}, realm_name=realm_name)
        client_roles = {
            role["id"]: role["name"]
            for role in keycloak_client.get_client_roles(client_id=client_id, realm_name=realm_name)
        }
        group_id = keycloak_client.get_group_id_by_path(realm_name=realm_name, path=group_name)
        if client_roles and set(roles).issubset(set(client_roles.values())):
            keycloak_client.assign_role_to_group(
                group_id=group_id,
                client_id=client_id,
                realm_name=realm_name,
                roles=[{"id": id, "name": name} for id, name in client_roles.items() if name in roles],
            )


def delete_keycloak_client(
    client_name: str,
    realm_name: str,
) -> None:
    """
    Delete keycloak client
    """
    keycloak_client: KeycloakAdminClient = get_keycloak_manager()
    try:
        keycloak_client.delete_client(client_name=client_name, realm_name=realm_name)
    except Exception as e:
        log_error(f"Keycloak client {client_name} not found in realm {realm_name} {e}")

    log_info(f"Keycloak client {client_name} deleted successfully")


def delete_keycloak_realm(
    client_name: str,
    realm_name: str,
) -> None:
    """
    Delete keycloak realm
    """
    keycloak_client: KeycloakAdminClient = get_keycloak_manager()
    try:
        keycloak_client.delete_realm(realm_name=realm_name, client_name=client_name)
    except Exception as e:
        log_error(f"Failed to delete realm {realm_name}: {e}")
    log_info(f"Keycloak realm {realm_name} deleted successfully")


def create_jeeves_idp_flow(
    tenant: str,
    realm_name: str,
    template_path: str,
    template_name: str,
    domain: str,
    is_prod: bool,
    template_payload: dict | None = None,
) -> None:
    """
    Create jeeves idp flow
    """
    idp_configs = template_render(
        template_path=template_path,
        template_name=template_name,
        template_payload={
            "tenant": tenant,
            "domain": domain,
            **(template_payload if template_payload else {}),
        },
    )

    idp_configs = ijson_loads(idp_configs)

    keycloak_client: KeycloakAdminClient = get_keycloak_manager(is_prod=is_prod)
    identity_providers = keycloak_client.get_identity_providers(realm_name=realm_name)
    try:
        for idp_config in idp_configs["identityProviders"]:
            if not py_.find(identity_providers, {"alias": idp_config["alias"]}):
                keycloak_client.create_identity_provider(idp_config, realm_name)
                for idp_mapper_config in idp_configs["identityProviderMappers"]:
                    if idp_mapper_config["identityProviderAlias"] == idp_config["alias"]:
                        keycloak_client.add_mapper_to_idp(
                            idp_alias=idp_mapper_config["identityProviderAlias"],
                            mapper_config=idp_mapper_config,
                            realm_name=realm_name,
                        )
    except Exception as e:
        log_error(f"Failed to create Keycloak idp and flows for {tenant=} with error: {e=}")
        return
    log_info(f"Keycloak idp and flows for {tenant} created successfully.")


def create_dexit_idp_flow(
    tenant: str,
    realm_name: str,
    template_path: str,
    template_name: str,
    domain: str,
    is_prod: bool,
    template_payload: dict | None = None,
) -> None:
    """
    Create dexit idp flow
    """
    idp_configs = template_render(
        template_path=template_path,
        template_name=template_name,
        template_payload={
            "tenant": tenant,
            "domain": domain,
            **(template_payload if template_payload else {}),
        },
    )

    idp_configs = ijson_loads(idp_configs)

    keycloak_client: KeycloakAdminClient = get_keycloak_manager(is_prod=is_prod)
    identity_providers = keycloak_client.get_identity_providers(realm_name=realm_name)
    try:
        for idp_config in idp_configs["identityProviders"]:
            if not py_.find(identity_providers, {"alias": idp_config["alias"]}):
                keycloak_client.create_identity_provider(idp_config, realm_name)
                for idp_mapper_config in idp_configs["identityProviderMappers"]:
                    if idp_mapper_config["identityProviderAlias"] == idp_config["alias"]:
                        keycloak_client.add_mapper_to_idp(
                            idp_alias=idp_mapper_config["identityProviderAlias"],
                            mapper_config=idp_mapper_config,
                            realm_name=realm_name,
                        )
    except Exception as e:
        log_error(f"Failed to create Keycloak idp and flows for {tenant=} in {realm_name} realm with error: {e=}")
        return
    log_info(f"Keycloak idp and flows for {tenant} created successfully in {realm_name} realm.")


class KeycloakRealmSetupActivityModel(LaunchpadCLIBaseModel):
    """
    KeycloakRealmSetupActivityModel
    """

    realm_name: str
    domain: str
    template_path: str
    template_name: str
    installer_secret: str | None = None
    template_payload: dict | None = None


class KeycloakRealmSetupActivity(Activity):
    """
    KeycloakRealmSetupActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="KeycloakRealmSetupActivity")
    async def defn(activity_model: KeycloakRealmSetupActivityModel) -> None:
        """
        Create keycloak realm
        """
        create_keycloak_realm(
            realm_name=activity_model.realm_name,
            domain=activity_model.domain,
            template_path=activity_model.template_path,
            template_name=activity_model.template_name,
            installer_secret=activity_model.installer_secret,
            template_payload=activity_model.template_payload,
        )

        log_info(f"Keycloak realm {activity_model.realm_name} created successfully")


class KeycloakClientSetupActivityModel(LaunchpadCLIBaseModel):
    """
    KeycloakClientSetupActivityModel
    """

    tenant: str
    realm_name: str
    domain: str
    template_path: str
    template_name: str
    is_prod: bool = False
    template_payload: dict | None = None
    auth_credential: str | None = None


class KeycloakClientSetupActivity(Activity):
    """
    KeycloakClientSetupActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="KeycloakClientSetupActivity")
    async def defn(activity_model: KeycloakClientSetupActivityModel) -> None:
        """
        Create keycloak client
        """
        create_keycloak_client(
            tenant=activity_model.tenant,
            realm_name=activity_model.realm_name,
            domain=activity_model.domain,
            template_path=activity_model.template_path,
            template_name=activity_model.template_name,
            auth_credential=activity_model.auth_credential,
            template_payload=activity_model.template_payload,
        )

        log_info(f"Keycloak client {activity_model.tenant} created successfully")


class KeycloakServiceAccountSetupActivityModel(LaunchpadCLIBaseModel):
    """
    KeycloakServiceAccountSetupActivityModel
    """

    tenant: str
    domain: str
    secret: str
    realm_name: str
    template_path: str
    template_name: str


class KeycloakServiceAccountSetupActivity(Activity):
    """
    KeycloakServiceAccountSetupActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="KeycloakServiceAccountSetupActivity")
    async def defn(activity_model: KeycloakServiceAccountSetupActivityModel) -> None:
        """
        Create keycloak service account
        """
        create_keycloak_service_account(
            tenant=activity_model.tenant,
            realm_name=activity_model.realm_name,
            domain=activity_model.domain,
            template_path=activity_model.template_path,
            template_name=activity_model.template_name,
            secret=activity_model.secret,
        )

        log_info(f"Keycloak service account {activity_model.tenant} created successfully")


class KeycloakCreateClientRolesActivityModel(LaunchpadCLIBaseModel):
    """
    KeycloakCreateClientRolesActivityModel
    """

    client_name: str
    realm_name: str
    roles: list[str]


class KeycloakCreateClientRolesActivity(Activity):
    """
    KeycloakCreateClientRolesActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="KeycloakCreateClientRolesActivity")
    async def defn(activity_model: KeycloakCreateClientRolesActivityModel) -> None:
        """
        Create keycloak client roles
        """
        create_client_roles(
            client_name=activity_model.client_name,
            realm_name=activity_model.realm_name,
            roles=activity_model.roles,
        )

        log_info(f"Keycloak client roles {activity_model.client_name} created successfully")


class KeycloakCreateTenantCustomerAdminUserActivityModel(LaunchpadCLIBaseModel):
    """
    KeycloakCreateTenantCustomerAdminUserActivityModel
    """

    realm_name: str
    client_name: str | None = None
    username: str
    email: str
    firstname: str
    lastname: str
    roles: list[str] | None = None
    template_path: str
    template_name: str
    group_path: str | None = None


class KeycloakCreateTenantCustomerAdminUserActivity(Activity):
    """
    KeycloakCreateTenantCustomerAdminUserActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="KeycloakCreateTenantCustomerAdminUserActivity")
    async def defn(activity_model: KeycloakCreateTenantCustomerAdminUserActivityModel) -> None:
        """
        Create keycloak tenant customer admin user
        """
        create_tenant_customer_admin_user(
            realm_name=activity_model.realm_name,
            client_name=activity_model.client_name,
            username=activity_model.username,
            email=activity_model.email,
            firstname=activity_model.firstname,
            lastname=activity_model.lastname,
            roles=activity_model.roles,
            template_path=activity_model.template_path,
            template_name=activity_model.template_name,
            group_path=activity_model.group_path,
        )

        log_info(f"Keycloak tenant customer admin user {activity_model.username} assigned to client roles successfully")


class KeycloakCreateInternalUsersActivityModel(LaunchpadCLIBaseModel):
    """
    KeycloakCreateInternalUsersActivityModel
    """

    realm_name: str
    client_name: str | None = None
    roles: list[str] | None = None
    template_path: str
    template_name: str
    users: list[dict]
    group_path: str | None = None


class KeycloakCreateInternalUsersActivity(Activity):
    """
    KeycloakCreateInternalUsersActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="KeycloakCreateInternalUsersActivity")
    async def defn(activity_model: KeycloakCreateInternalUsersActivityModel) -> None:
        """
        Create keycloak internal users
        """
        create_internal_users(
            realm_name=activity_model.realm_name,
            client_name=activity_model.client_name,
            roles=activity_model.roles,
            template_path=activity_model.template_path,
            template_name=activity_model.template_name,
            users=activity_model.users,
            group_path=activity_model.group_path,
        )

        log_info(f"Created {len(activity_model.users)} keycloak internal users successfully")


class DeleteKeycloakClientActivityModel(LaunchpadCLIBaseModel):
    """
    DeleteKeycloakClientActivityModel
    """

    client_name: str
    realm_name: str


class DeleteKeycloakClientActivity(Activity):
    """
    DeleteKeycloakClientActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="DeleteKeycloakClientActivity")
    async def defn(activity_model: DeleteKeycloakClientActivityModel) -> None:
        """
        Delete keycloak client
        """
        delete_keycloak_client(
            client_name=activity_model.client_name,
            realm_name=activity_model.realm_name,
        )


class KeycloakCreateIDPFlowActivity(Activity):
    """
    KeycloakCreateIDPFlowActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="KeycloakCreateIDPFlowActivity")
    async def defn(activity_model: KeycloakClientSetupActivityModel) -> None:
        """
        Create keycloak client
        """
        jinja_env: jinja2.Environment = get_env(template_path=activity_model.template_path)
        template = jinja_env.get_template(activity_model.template_name)

        googleclientid = OnePasswordUtil(
            tenant="INTEGRATION_COMMON_CONFIG", server_item="application-config", vault="Penknife"
        ).get_key("provider_client_id")

        googlesecret = OnePasswordUtil(
            tenant="INTEGRATION_COMMON_CONFIG", server_item="application-config", vault="Penknife"
        ).get_key("provider_client_secret")

        client_config = template.render(googleclientid=googleclientid, googlesecret=googlesecret)
        client_config = ijson_loads(client_config)
        # authentication flows creation is moved to realm creation config
        idp_configs = client_config["identityProviders"]
        idp_mapper_configs = client_config["identityProviderMappers"]

        keycloak_client: KeycloakAdminClient = get_keycloak_manager()

        identity_providers = keycloak_client.get_identity_providers(realm_name=activity_model.realm_name)
        for idp_config in idp_configs:
            if not py_.find(identity_providers, {"alias": idp_config["alias"]}):
                keycloak_client.create_identity_provider(idp_config, activity_model.realm_name)
                for idp_mapper_config in idp_mapper_configs:
                    if idp_mapper_config["identityProviderAlias"] == idp_config["alias"]:
                        keycloak_client.add_mapper_to_idp(
                            idp_alias=idp_mapper_config["identityProviderAlias"],
                            mapper_config=idp_mapper_config,
                            realm_name=activity_model.realm_name,
                        )

        log_info(f"Keycloak idp and flows for {activity_model.tenant} created successfully.")


class JeevesKeycloakCreateIDPFlowActivity(Activity):
    """
    JeevesKeycloakCreateIDPFlowActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="JeevesKeycloakCreateIDPFlowActivity")
    async def defn(activity_model: KeycloakClientSetupActivityModel) -> None:
        """
        Create keycloak client
        """
        create_jeeves_idp_flow(
            tenant=activity_model.tenant,
            realm_name=activity_model.realm_name,
            template_path=activity_model.template_path,
            template_name=activity_model.template_name,
            domain=activity_model.domain,
            template_payload=activity_model.template_payload,
            is_prod=activity_model.is_prod,
        )


class DeleteIdpFromHelpinstanceActivityModel(LaunchpadCLIBaseModel):
    """
    DeleteIdpFromHelpinstanceActivityModel
    """

    tenant: str
    is_prod: bool = False


class DeleteIdpFromHelpinstanceActivity(Activity):
    """
    DeleteIdpFromHelpinstanceActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="DeleteIdpFromHelpinstanceActivity")
    async def defn(activity_model: DeleteIdpFromHelpinstanceActivityModel) -> None:
        """
        Delete keycloak client
        """
        keycloak_client: KeycloakAdminClient = get_keycloak_manager(is_prod=True)
        try:
            keycloak_client.delete_idp(idp_alias=f"jeeves-{activity_model.tenant}", realm_name="help")
        except Exception as e:
            log_error(f"Failed to delete identity provider {e}")


class DeleteKeycloakRealmActivityModel(LaunchpadCLIBaseModel):
    """
    DeleteKeycloakRealmActivityModel
    """

    client_name: str
    realm_name: str


class DeleteKeycloakRealmActivity(Activity):
    """
    DeleteKeycloakRealmActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="DeleteKeycloakRealmActivity")
    async def defn(activity_model: DeleteKeycloakRealmActivityModel) -> None:
        """
        Delete keycloak client
        """
        delete_keycloak_realm(
            client_name=activity_model.client_name,
            realm_name=activity_model.realm_name,
        )


class DexitKeycloakCreateIDPFlowActivity(Activity):
    """
    DexitKeycloakCreateIDPFlowActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="DexitKeycloakCreateIDPFlowActivity")
    async def defn(activity_model: KeycloakClientSetupActivityModel) -> None:
        """
        Create keycloak IDP in {realm_name} realm
        """
        create_dexit_idp_flow(
            tenant=activity_model.tenant,
            realm_name=activity_model.realm_name,
            template_path=activity_model.template_path,
            template_name=activity_model.template_name,
            domain=activity_model.domain,
            template_payload=activity_model.template_payload,
            is_prod=activity_model.is_prod,
        )


class DeleteIdpFromDexithelpActivityModel(LaunchpadCLIBaseModel):
    """
    DeleteIdpFromDexithelpActivityModel
    """

    tenant: str
    is_prod: bool = False


class DeleteIdpFromDexithelpActivity(Activity):
    """
    DeleteIdpFromDexithelpActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="DeleteIdpFromDexithelpActivity")
    async def defn(activity_model: DeleteIdpFromDexithelpActivityModel) -> None:
        """
        Delete IDP from dexithelp realm
        """
        keycloak_client: KeycloakAdminClient = get_keycloak_manager(is_prod=activity_model.is_prod)
        try:
            keycloak_client.delete_idp(idp_alias=f"{activity_model.tenant}", realm_name="dexithelp")
        except Exception as e:
            log_error(f"Failed to delete identity provider from dexithelp realm: {e}")


class KeycloakCreateGroupActivityModel(LaunchpadCLIBaseModel):
    """
    KeycloakCreateGroupActivity
    """

    realm_name: str
    client_name: str | None = None
    template_path: str
    template_name: str


class KeycloakCreateGroupActivity(Activity):
    """
    KeycloakCreateGroupActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="KeycloakCreateGroupActivity")
    async def defn(activity_model: KeycloakCreateGroupActivityModel) -> None:
        """
        Create keycloak groups
        """
        create_keycloak_group(
            realm_name=activity_model.realm_name,
            client_name=activity_model.client_name,
            template_path=activity_model.template_path,
            template_name=activity_model.template_name,
        )

        log_info("Created keycloak Groups successfully")
