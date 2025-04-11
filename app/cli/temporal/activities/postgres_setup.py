import base64
from datetime import timedelta

import aiohttp
import httpx
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.k8s_util import get_k8s_core_v1_api_client
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_error, log_info
from app.core.db import DBManager, get_super_admin_db_manager
from app.core.settings import AppSettings, get_settings
from app.template_env import get_env


class PostgresSchemaCreationActivityModel(LaunchpadCLIBaseModel):
    """
    PostgresSchemaCreationActivityModel
    """

    schema_name: str
    username: str
    database_name: str


class PostgresSchemaCreationActivity(Activity):
    """
    PostgresSchemaCreationActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        timeout for the activity
        """
        return timedelta(seconds=30)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="PostgresSchemaCreationActivity")
    async def defn(activity_model: PostgresSchemaCreationActivityModel) -> None:
        """
        Setup postgres
        """
        db: DBManager = await get_super_admin_db_manager()

        await db.execute_raw_sql(
            f'CREATE SCHEMA IF NOT EXISTS "{activity_model.schema_name}" AUTHORIZATION {activity_model.username};',
        )
        log_info(f"Created schema {activity_model.schema_name} for user {activity_model.username}")


# Create user
class PostgresUserCreationActivityModel(LaunchpadCLIBaseModel):
    """
    PostgresUserCreationActivityModel
    """

    username: str
    password: str
    database_name: str


class PostgresUserCreationActivity(Activity):
    """
    PostgresUserCreationActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        timeout for the activity
        """
        return timedelta(seconds=30)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="PostgresUserCreationActivity")
    async def defn(activity_model: PostgresUserCreationActivityModel) -> None:
        """
        Setup postgres
        """
        # check if user exists and if not create user
        db: DBManager = await get_super_admin_db_manager()

        response = await db.fetch_one(
            sqlfile="check_if_user_exists.sql",
            username=activity_model.username,
        )

        if response is None:
            await db.execute_raw_sql(
                query=f"CREATE ROLE {activity_model.username} NOSUPERUSER NOCREATEDB"
                " NOCREATEROLE INHERIT LOGIN PASSWORD '{activity_model.password}';",
            )
            log_info(f"Created user {activity_model.username} with password {activity_model.password}")
        else:
            await db.execute_raw_sql(
                query=f"ALTER USER {activity_model.username} WITH PASSWORD '{activity_model.password}';",
            )
            log_info(f"Updated password for user {activity_model.username} successfully.")


class PostgresUserCreationFromSecretActivityModel(LaunchpadCLIBaseModel):
    """
    PostgresUserCreationActivityModel
    """

    secret_name: str
    database_name: str
    username: str
    namespace: str
    password_key: str = "password"


class PostgresUserCreationFromSecretActivity(Activity):
    """
    PostgresUserCreationFromSecretActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        timeout for the activity
        """
        return timedelta(seconds=30)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="PostgresUserCreationFromSecretActivity")
    async def defn(activity_model: PostgresUserCreationFromSecretActivityModel) -> None:
        """
        Setup postgres
        """
        # check if user exists and if not create user
        db: DBManager = await get_super_admin_db_manager()

        response = await db.fetch_one(
            sqlfile="check_if_user_exists.sql",
            username=activity_model.username,
        )
        k8s_client = get_k8s_core_v1_api_client()
        secret = k8s_client.read_namespaced_secret(
            name=activity_model.secret_name,
            namespace=activity_model.namespace,
        )
        username = activity_model.username
        password = base64.b64decode(secret.data[activity_model.password_key]).decode()

        if response is None:
            query = f"CREATE ROLE {username} NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT LOGIN PASSWORD '{password}';"
            await db.execute_raw_sql(query=query)
            log_info(f"Created user {username}")
        else:
            await db.execute_raw_sql(query=f"ALTER USER {username} WITH PASSWORD '{password}';")
            log_info(f"Updated password for user {username} successfully.")


class PostgresDatabaseCreationActivityModel(LaunchpadCLIBaseModel):
    """
    PostgresDatabaseCreationActivityModel
    """

    database_name: str


class PostgresDatabaseCreationActivity(Activity):
    """
    PostgresDatabaseCreationActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        timeout for the activity
        """
        return timedelta(seconds=30)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="PostgresDatabaseCreationActivity")
    async def defn(activity_model: PostgresDatabaseCreationActivityModel) -> None:
        """
        Setup postgres
        """
        db: DBManager = await get_super_admin_db_manager()

        database_exists = await db.fetch_one(
            sqlfile="check_if_database_exists.sql",
            database_name=activity_model.database_name,
        )
        if not database_exists:
            await db.create_database(db_name=activity_model.database_name)
            log_info(f"Created database {activity_model.database_name}")


class PostgresGrantAccessToUserActivityModel(LaunchpadCLIBaseModel):
    """
    PostgresGrantAccessToUserActivityModel
    """

    username: str
    database_name: str
    schema_name: str | None = None


class PostgresGrantAccessToUserActivity(Activity):
    """
    PostgresGrantAccessToUserActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        timeout for the activity
        """
        return timedelta(seconds=30)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="PostgresGrantAccessToUserActivity")
    async def defn(activity_model: PostgresGrantAccessToUserActivityModel) -> None:
        """
        Setup postgres
        """
        db: DBManager = await get_super_admin_db_manager()

        await db.execute_raw_sql(
            query=f'GRANT CONNECT, CREATE ON DATABASE "{activity_model.database_name}" TO {activity_model.username};',
        )

        log_info(
            f"Granted user {activity_model.username} to connect and create on database {activity_model.database_name}"
        )

        for schema in ["public", activity_model.schema_name]:
            if schema:
                await db.execute_raw_sql(
                    query=f'GRANT ALL ON SCHEMA "{schema}" TO {activity_model.username};',
                )

                log_info(f"Granted user {activity_model.username} all privileges on schema {schema}")


class KeycloakUserMappingActivityModel(LaunchpadCLIBaseModel):
    """
    KeycloakUserMappingActivityModel
    """

    username: str
    database_name: str


class KeycloakUserMappingActivity(Activity):
    """
    KeycloakUserMappingActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        timeout for the activity
        """
        return timedelta(seconds=30)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="KeycloakUserMappingActivity")
    async def defn(activity_model: KeycloakUserMappingActivityModel) -> None:
        """
        Setup postgres
        """
        config: AppSettings = get_settings()
        db: DBManager = await get_super_admin_db_manager()

        await db.execute_raw_sql(
            query=f"CREATE USER MAPPING IF NOT EXISTS FOR {activity_model.username} SERVER keycloak_server OPTIONS  "
            f"(user 'keyclock_fdw', password '{config.keycloak.keycloak_db_password}');",
        )
        log_info("Created user mapping for keycloak database successfully.")


class MatomoUserMappingActivityModel(LaunchpadCLIBaseModel):
    """
    MatomoUserMappingActivityModel
    """

    username: str
    database_name: str


class MatomoUserMappingActivity(Activity):
    """
    MatomoUserMappingActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        timeout for the activity
        """
        return timedelta(seconds=30)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="MatomoUserMappingActivity")
    async def defn(activity_model: MatomoUserMappingActivityModel) -> None:
        """
        Setup postgres
        """
        config: AppSettings = get_settings()
        db: DBManager = await get_super_admin_db_manager()

        await db.execute_raw_sql(
            query=f"CREATE USER MAPPING IF NOT EXISTS FOR {activity_model.username} SERVER matomo_server OPTIONS  "
            f"(username 'matomo_fdw', password '{config.matomo_db_password}');",
        )
        log_info("Created user mapping for matomo database successfully.")


class TableSpaceActivityModel(LaunchpadCLIBaseModel):
    """
    TableSpaceActivityModel
    """

    username: str
    database_name: str


class TableSpaceActivity(Activity):
    """
    TableSpaceActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        timeout for the activity
        """
        return timedelta(seconds=30)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="TableSpaceActivity")
    async def defn(activity_model: TableSpaceActivityModel) -> None:
        """
        Setup postgres
        """
        db: DBManager = await get_super_admin_db_manager()

        await db.execute_raw_sql(query=f"GRANT CREATE ON TABLESPACE pgdataenc TO {activity_model.username};")
        log_info(f"Granted user {activity_model.username} create role on tablespace pgdataenc successfully.")


class PostgresGrantAllPrivilegesOnTableActivityModel(LaunchpadCLIBaseModel):
    """
    PostgresGrantAllPrivilegesOnTableActivityModel
    """

    username: str
    database_name: str
    tables: list[str]


class PostgresGrantAllPrivilegesOnTableActivity(Activity):
    """
    PostgresGrantAllPrivilegesOnTableActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        timeout for the activity
        """
        return timedelta(seconds=30)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="PostgresGrantAllPrivilegesOnTableActivity")
    async def defn(activity_model: PostgresGrantAllPrivilegesOnTableActivityModel) -> None:
        """
        Setup postgres
        """
        db: DBManager = await get_super_admin_db_manager()
        for table in activity_model.tables:
            await db.execute_raw_sql(
                query=f"GRANT ALL PRIVILEGES ON TABLE {table} TO {activity_model.username};",
            )
            log_info(f"Granted user {activity_model.username} all privileges on table {table} successfully.")


class PostgresSupavisorPollUserActivityModel(LaunchpadCLIBaseModel):
    """
    PostgresSupavisorPollUserActivityModel
    """

    username: str
    database_name: str
    db_password: str
    template_path: str


class PostgresSupavisorPollUserActivity(Activity):
    """
    PostgresSupavisorPollUserActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        timeout for the activity
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="PostgresSupavisorPollUserActivity")
    async def defn(activity_model: PostgresSupavisorPollUserActivityModel) -> None:
        """
        Setup postgres
        """
        config: AppSettings = get_settings()

        environment: str = config.env

        jinja_env = get_env(template_path=activity_model.template_path)
        template = jinja_env.get_template(f"{environment}-supavisor-user.json")
        rendered_template = template.render(
            DATABASE=activity_model.database_name.lower(),
            DB_USER=activity_model.username,
            DB_PASSWORD=activity_model.db_password,
        )

        async with httpx.AsyncClient() as session:
            response = await session.put(
                url=f"{config.supavisor_url}/api/tenants/{activity_model.username}",
                headers={
                    "Authorization": f"Bearer {config.supavisor_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                content=rendered_template,
                timeout=httpx.Timeout(120),
            )

            if response.status_code < 200 or response.status_code >= 299:
                response_json = response.text
                log_error(
                    f"Supavisor user creation failed with status: {response.status_code} and response: {response_json}"
                )
                raise aiohttp.ClientResponseError(
                    request_info=aiohttp.RequestInfo(
                        url=f"{config.supavisor_url}/api/tenants/{activity_model.username}",
                        method="PUT",
                        headers={"Authorization": f"Bearer {config.supavisor_token}"},
                    ),
                    history=(),
                    status=response.status_code,
                    message=f"Supavisor user creation failed with status code: {response.status_code}",
                )
        log_info(f"Supervisor poll user created: {activity_model.username}")


class DeleteSupavisorTenantActivityModel(LaunchpadCLIBaseModel):
    """
    DeleteSupavisorTenantActivityModel
    """

    supavisor_tenant_name: str


class DeleteSupavisorTenantActivity(Activity):
    """
    DeleteSupavisorTenantActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        timeout for the activity
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="DeleteSupavisorTenantActivity")
    async def defn(activity_model: DeleteSupavisorTenantActivityModel) -> None:
        """
        Setup postgres
        """
        config: AppSettings = get_settings()

        async with aiohttp.ClientSession() as session:
            response = await session.delete(
                url=f"{config.supavisor_url}/api/tenants/{activity_model.supavisor_tenant_name}",
                headers={
                    "Authorization": f"Bearer {config.supavisor_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=120),
            )

            if response.status < 200 or response.status >= 299:
                response_json = await response.json()
                log_error(
                    f"Supavisor user deletion failed with status code: {response.status} and response: {response_json}"
                )
                raise aiohttp.ClientResponseError(
                    request_info=aiohttp.RequestInfo(
                        url=f"{config.supavisor_url}/api/tenants/{activity_model.username}",
                        method="DELETE",
                        headers={"Authorization": f"Bearer {config.supavisor_token}"},
                    ),
                    history=(),
                    status=response.status,
                    message=f"Supavisor user creation failed with status code: {response.status}",
                )
        log_info(f"Supervisor poll user created: {activity_model.username}")


class DeletePostgresUserActivityModel(LaunchpadCLIBaseModel):
    """
    DeletePostgresUserActivityModel
    """

    username: str
    database_name: str


class DeletePostgresUserActivity(Activity):
    """
    DeletePostgresUserActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        timeout for the activity
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="DeletePostgresUserActivity")
    async def defn(activity_model: DeletePostgresUserActivityModel) -> None:
        """
        Setup postgres
        """
        db: DBManager = await get_super_admin_db_manager()

        await db.execute_raw_sql(query=f"DROP USER IF EXISTS {activity_model.username};")
        log_info(f"Deleted user {activity_model.username} successfully.")


class DeletePostgresSchemaActivityModel(LaunchpadCLIBaseModel):
    """
    DeletePostgresSchemaActivityModel
    """

    schema_name: str
    database_name: str


class DeletePostgresSchemaActivity(Activity):
    """
    DeletePostgresSchemaActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        timeout for the activity
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="DeletePostgresSchemaActivity")
    async def defn(activity_model: DeletePostgresSchemaActivityModel) -> None:
        """
        Setup postgres
        """
        db: DBManager = await get_super_admin_db_manager()

        await db.execute_raw_sql(query=f"DROP SCHEMA IF EXISTS {activity_model.schema_name} CASCADE;")
        log_info(f"Deleted schema {activity_model.schema_name} successfully.")
