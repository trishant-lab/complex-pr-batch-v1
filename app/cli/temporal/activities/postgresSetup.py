import requests
from temporalio import activity
from temporalio.common import RetryPolicy
from datetime import timedelta

from app.cli.temporal.core.base import LaunchpadCLIBaseModel
from app.cli.temporal.core.base import Activity
from app.cli.temporal.core.log import log_error, log_info
from app.core.db import DBManager, get_db_manager
from app.core.settings import AppSettings, get_settings
from app.template_env import get_env


class PostgresSchemaCreationActivityModel(LaunchpadCLIBaseModel):
    """
    PostgresSchemaCreationActivityModel
    """

    schema_name: str
    username: str


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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)

    @staticmethod
    @activity.defn(name="PostgresSchemaCreationActivity")
    async def defn(activity_model: PostgresSchemaCreationActivityModel) -> None:
        """
        Setup postgres
        """
        config: AppSettings = get_settings()

        db: DBManager = await get_db_manager(dsn=config.postgres.dsn)

        await db.execute_raw_sql(
            f"CREATE SCHEMA IF NOT EXISTS {activity_model.schema_name} AUTHORIZATION {activity_model.username};",
        )

        log_info(f"Created schema {activity_model.schema_name} for user {activity_model.username}")


# Create user


class PostgresUserCreationActivityModel(LaunchpadCLIBaseModel):
    """
    PostgresUserCreationActivityModel
    """

    username: str
    password: str


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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)

    @staticmethod
    @activity.defn(name="PostgresUserCreationActivity")
    async def defn(activity_model: PostgresUserCreationActivityModel) -> None:
        """
        Setup postgres
        """
        # check if user exists and if not create user

        config: AppSettings = get_settings()

        db: DBManager = await get_db_manager(dsn=config.postgres.dsn)

        response = await db.fetch_one(
            sqlfile="checkIfUserExists.sql",
            username=activity_model.username,
        )

        if not dict(response):
            await db.execute_raw_sql(
                query=f"CREATE ROLE {activity_model.username} NOSUPERUSER NOCREATEDB"
                " NOCREATEROLE INHERIT LOGIN PASSWORD '{activity_model.password}';",
            )

        log_info(f"Created user {activity_model.username} with password {activity_model.password}")


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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)

    @staticmethod
    @activity.defn(name="PostgresDatabaseCreationActivity")
    async def defn(activity_model: PostgresDatabaseCreationActivityModel) -> None:
        """
        Setup postgres
        """
        config: AppSettings = get_settings()

        db: DBManager = await get_db_manager(dsn=config.postgres.dsn)

        await db.create_database(db_name=activity_model.database_name)

        log_info(f"Created database {activity_model.database_name}")


class PostgresGrantAccessToUserActivityModel(LaunchpadCLIBaseModel):
    """
    PostgresGrantAccessToUserActivityModel
    """

    username: str
    database_name: str
    schema_name: str


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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)

    @staticmethod
    @activity.defn(name="PostgresGrantAccessToUserActivity")
    async def defn(activity_model: PostgresGrantAccessToUserActivityModel) -> None:
        """
        Setup postgres
        """
        config: AppSettings = get_settings()

        db: DBManager = await get_db_manager(dsn=config.postgres.dsn)

        await db.execute_raw_sql(
            query=f"GRANT CONNECT, CREATE ON DATABASE {activity_model.database_name} TO {activity_model.    username};",
        )

        log_info(
            f"Granted user {activity_model.username} to connect and create on database {activity_model.database_name}"
        )

        for schema in ["public", activity_model.schema_name]:
            await db.execute_raw_sql(
                query=f"GRANT ALL ON SCHEMA {schema} TO {activity_model.username};",
            )

            log_info(f"Granted user {activity_model.username} all privileges on schema {schema}")


class KeycloakUserMappingActivityModel(LaunchpadCLIBaseModel):
    """
    KeycloakUserMappingActivityModel
    """

    username: str


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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)

    @staticmethod
    @activity.defn(name="KeycloakUserMappingActivity")
    async def defn(activity_model: KeycloakUserMappingActivityModel) -> None:
        """
        Setup postgres
        """
        config: AppSettings = get_settings()

        db: DBManager = await get_db_manager(dsn=config.postgres.dsn)

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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)

    @staticmethod
    @activity.defn(name="MatomoUserMappingActivity")
    async def defn(activity_model: MatomoUserMappingActivityModel) -> None:
        """
        Setup postgres
        """
        config: AppSettings = get_settings()

        db: DBManager = await get_db_manager(dsn=config.postgres.dsn)

        await db.execute_raw_sql(
            query=f"CREATE USER MAPPING IF NOT EXISTS FOR {activity_model.username} SERVER matomo_server OPTIONS  "
            f"(user 'matomo_fdw', password '{config.matomo_db_password}');",
        )
        log_info("Created user mapping for matomo database successfully.")


class TableSpaceActivityModel(LaunchpadCLIBaseModel):
    """
    TableSpaceActivityModel
    """

    username: str


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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)

    @staticmethod
    @activity.defn(name="TableSpaceActivity")
    async def defn(activity_model: TableSpaceActivityModel) -> None:
        """
        Setup postgres
        """
        config: AppSettings = get_settings()

        db: DBManager = await get_db_manager(dsn=config.postgres.dsn)

        await db.execute_raw_sql(
            query=f"GRANT CREATE ON TABLESPACE pgdataenc TO {activity_model.username};",
        )
        log_info(f"Granted user {activity_model.username} create role on tablespace pgdataenc successfully.")


class PostgresGrantAllPrivilegesOnTableActivityModel(LaunchpadCLIBaseModel):
    """
    PostgresGrantAllPrivilegesOnTableActivityModel
    """

    username: str
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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)

    @staticmethod
    @activity.defn(name="PostgresGrantAllPrivilegesOnTableActivity")
    async def defn(activity_model: PostgresGrantAllPrivilegesOnTableActivityModel) -> None:
        """
        Setup postgres
        """
        config: AppSettings = get_settings()

        db: DBManager = await get_db_manager(dsn=config.postgres.dsn)

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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)

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

        response = requests.put(
            url=f"{config.supavisor_url}/api/tenants/{activity_model.username}",
            headers={
                "Authorization": f"Bearer {config.supavisor_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            data=rendered_template,
            timeout=120,
        )

        if response.status_code < 200 or response.status_code >= 299:
            log_error(f"Supavisor user creation failed with status code: {response.status_code}")
            raise Exception(f"Supavisor user creation failed with status code: {response.status_code}")
        log_info(f"Supervisor poll user created: {activity_model.username}")
