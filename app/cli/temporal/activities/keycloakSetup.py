from temporalio import activity, workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from datetime import timedelta
    import jinja2
    import orjson
    from app.cli.keycloakUtils import KeycloakAdminClient, get_keycloak_manager
    from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
    from app.cli.temporal.core.log import log_info
    from app.core.settings import AppSettings, get_settings
    from app.template_env import get_env


class KeycloakRealmSetupActivityModel(LaunchpadCLIBaseModel):
    """
    KeycloakRealmSetupActivityModel
    """

    tenant: str
    domain: str
    template_path: str
    template_name: str


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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)

    @staticmethod
    @activity.defn(name="KeycloakRealmSetupActivity")
    async def defn(activity_model: KeycloakRealmSetupActivityModel) -> None:
        """
        Create keycloak realm
        """
        config: AppSettings = get_settings()

        jinja_env: jinja2.Environment = get_env(template_path=activity_model.template_path)
        template = jinja_env.get_template(activity_model.template_name)

        realm_config = template.render(
            tenant=activity_model.tenant,
            sendgrid_api_key=config.sendgrid.api_key,
            domain=activity_model.domain,
        )

        keycloak_client: KeycloakAdminClient = get_keycloak_manager()
        keycloak_client.create_realm(orjson.loads(realm_config), skip_exists=True)

        log_info(f"Keycloak realm {activity_model.tenant} created successfully")


class KeycloakClientSetupActivityModel(LaunchpadCLIBaseModel):
    """
    KeycloakClientSetupActivityModel
    """

    tenant: str
    realm_name: str
    domain: str
    template_path: str
    template_name: str


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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)

    @staticmethod
    @activity.defn(name="KeycloakClientSetupActivity")
    async def defn(activity_model: KeycloakClientSetupActivityModel) -> None:
        """
        Create keycloak client
        """
        jinja_env: jinja2.Environment = get_env(template_path=activity_model.template_path)
        template = jinja_env.get_template(activity_model.template_name)
        client_config = template.render(
            tenant=activity_model.tenant,
            domain=activity_model.domain,
        )

        keycloak_client: KeycloakAdminClient = get_keycloak_manager()
        keycloak_client.create_client(orjson.loads(client_config), activity_model.realm_name)

        log_info(f"Keycloak client {activity_model.tenant} created successfully")


class KeycloakServiceAccountSetupActivityModel(LaunchpadCLIBaseModel):
    """
    KeycloakServiceAccountSetupActivityModel
    """

    tenant: str
    domain: str
    secret: str
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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)

    @staticmethod
    @activity.defn(name="KeycloakServiceAccountSetupActivity")
    async def defn(activity_model: KeycloakServiceAccountSetupActivityModel) -> None:
        """
        Create keycloak service account
        """
        jinja_env: jinja2.Environment = get_env(template_path=activity_model.template_path)
        template = jinja_env.get_template(activity_model.template_name)
        service_account_config = template.render(
            tenant=activity_model.tenant,
            domain=activity_model.domain,
            secret=activity_model.secret,
        )

        keycloak_client: KeycloakAdminClient = get_keycloak_manager()
        keycloak_client.create_client(orjson.loads(service_account_config), activity_model.realm_name)

        log_info(f"Keycloak service account {activity_model.client_name} created successfully")


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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)

    @staticmethod
    @activity.defn(name="KeycloakCreateClientRolesActivity")
    async def defn(activity_model: KeycloakCreateClientRolesActivityModel) -> None:
        """
        Create keycloak client roles
        """
        keycloak_client: KeycloakAdminClient = get_keycloak_manager()

        client_uuid = keycloak_client.get_client_id(
            client=activity_model.client_name, realm_name=activity_model.realm_name
        )

        for role in activity_model.roles:
            keycloak_client.create_client_role(
                client_id=client_uuid, role_config={"name": role}, realm_name=activity_model.realm_name
            )

        log_info(f"Keycloak client roles {activity_model.client_name} created successfully")


class KeycloakCreateTenantCustomerAdminUserActivityModel(LaunchpadCLIBaseModel):
    """
    KeycloakCreateTenantCustomerAdminUserActivityModel
    """

    realm_name: str
    client_name: str
    username: str
    email: str
    firstname: str
    lastname: str
    roles: list[str] | None = None
    template_path: str
    template_name: str


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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)

    @staticmethod
    @activity.defn(name="KeycloakCreateTenantCustomerAdminUserActivity")
    async def defn(activity_model: KeycloakCreateTenantCustomerAdminUserActivityModel) -> None:
        """
        Create keycloak tenant customer admin user
        """
        jinja_env: jinja2.Environment = get_env(template_path=activity_model.template_path)
        template = jinja_env.get_template(activity_model.template_name)
        user_config = template.render(
            username=activity_model.username,
            email=activity_model.email,
            firstname=activity_model.firstname,
            lastname=activity_model.lastname,
        )

        keycloak_client: KeycloakAdminClient = get_keycloak_manager()

        keycloak_client.create_user(orjson.loads(user_config), activity_model.realm_name)

        log_info(f"Keycloak tenant customer admin user {activity_model.username} created successfully")

        client_uuid = keycloak_client.get_client_id(
            client=activity_model.client_name, realm_name=activity_model.realm_name
        )

        if not activity_model.roles:
            roles = keycloak_client.get_client_roles(client_id=client_uuid, realm_name=activity_model.realm_name)
        else:
            roles = activity_model.roles

        keycloak_client.assign_client_role(
            client_id=client_uuid,
            user_id=keycloak_client.get_user_id(username=activity_model.email, realm_name=activity_model.realm_name),
            roles=roles,
            realm_name=activity_model.realm_name,
        )

        log_info(f"Keycloak tenant customer admin user {activity_model.username} assigned to client roles successfully")


class KeycloakCreateInternalUsersActivityModel(LaunchpadCLIBaseModel):
    """
    KeycloakCreateInternalUsersActivityModel
    """

    realm_name: str
    client_name: str
    roles: list[str] | None = None
    template_path: str
    template_name: str
    users: list[dict]


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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)

    @staticmethod
    @activity.defn(name="KeycloakCreateInternalUsersActivity")
    async def defn(activity_model: KeycloakCreateInternalUsersActivityModel) -> None:
        """
        Create keycloak internal users
        """
        jinja_env: jinja2.Environment = get_env(template_path=activity_model.template_path)
        template = jinja_env.get_template(activity_model.template_name)

        keycloak_client: KeycloakAdminClient = get_keycloak_manager()

        client_id = keycloak_client.get_client_id(
            client=activity_model.client_name, realm_name=activity_model.realm_name
        )

        if not activity_model.roles:
            roles = keycloak_client.get_client_roles(client_id=client_id, realm_name=activity_model.realm_name)
        else:
            roles = activity_model.roles

        for user in activity_model.users:
            user_config = template.render(
                username=user["username"],
                email=user["email"],
                firstname=user["firstname"],
                lastname=user["lastname"],
            )

            keycloak_client.create_user(orjson.loads(user_config), activity_model.realm_name)

            log_info(f"Keycloak internal user {user['username']} created successfully")

            keycloak_client.assign_client_role(
                client_id=client_id,
                user_id=keycloak_client.get_user_id(username=user["username"], realm_name=activity_model.realm_name),
                roles=roles,
                realm_name=activity_model.realm_name,
            )

            log_info(f"Keycloak internal user {user['username']} assigned to client roles successfully")
