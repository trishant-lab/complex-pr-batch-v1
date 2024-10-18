from app.cli.temporal.core.log import log_info
from app.core.db import DBManager


class PostgresUtils:
    """
    PostgresUtils class
    """

    def __init__(self: "PostgresUtils", db: DBManager) -> None:
        """
        Constructor
        """
        self.db: DBManager = db

    async def create_user(self: "PostgresUtils", username: str, password: str) -> None:
        """
        Create a new user in the database
        """
        await self.db.execute_raw_sql(
            query=f"CREATE ROLE {username} NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT LOGIN PASSWORD '{password}';",
        )
        log_info(f"Created user {username} successfully.")

    async def update_user_password(self: "PostgresUtils", username: str, password: str) -> None:
        """
        Update user password in the database
        """
        await self.db.execute_raw_sql(
            query=f"ALTER USER {username} WITH PASSWORD '{password}';",
        )
        log_info(f"Updated password for user {username} successfully.")

    async def create_database(self: "PostgresUtils", database_name: str) -> None:
        """
        Create a new database in the database
        """
        await self.db.create_database(db_name=database_name)
        log_info(f"Created database {database_name} successfully.")

    async def check_if_database_exists(self: "PostgresUtils", database_name: str) -> bool:
        """
        Check if the database already exists in the database
        """
        return await self.db.fetch_one(
            sqlfile="checkIfDatabaseExists.sql",
            database_name=database_name,
        )

    async def create_schema(self: "PostgresUtils", schema_name: str, username: str) -> None:
        """
        Create a new schema in the database
        """
        await self.db.execute_raw_sql(
            f"CREATE SCHEMA IF NOT EXISTS { schema_name } AUTHORIZATION { username };",
        )
        log_info(f"Created schema {schema_name} successfully.")

    async def check_if_user_exists(self: "PostgresUtils", username: str) -> dict:
        """
        Check if the user already exists in the database
        """
        response = await self.db.fetch_one(
            sqlfile="checkIfUserExists.sql",
            username=username,
        )
        return dict(response) if response else {}

    async def grant_user_to_connect_and_create(self: "PostgresUtils", username: str, database: str) -> None:
        """
        Grant user to connect and create on the database
        """
        # Grant permissions
        await self.db.execute_raw_sql(
            query=f"GRANT CONNECT, CREATE ON DATABASE {database} TO {username};",
        )
        log_info(f"Granted user {username} to connect and create on database {database} successfully.")

    async def grant_user_all_privileges_on_schema(self: "PostgresUtils", username: str, schema_name: str) -> None:
        """
        Grant all privileges on the schema to the user
        """
        # Grant permissions
        await self.db.execute_raw_sql(
            query=f"GRANT ALL ON SCHEMA {schema_name} TO {username}",
        )
        log_info(f"Granted user {username} all privileges on schema {schema_name} successfully.")

    async def create_user_mapping_for_keycloak(self: "PostgresUtils", username: str, keycloak_password: str) -> None:
        """
        Create user mapping for keycloak
        """
        await self.db.execute_raw_sql(
            query=f"CREATE USER MAPPING IF NOT EXISTS FOR {username} SERVER keycloak_server OPTIONS  "
            f"(user 'keyclock_fdw', password '{keycloak_password}');",
        )
        log_info("Created user mapping for keycloak database successfully.")

    async def grant_user_all_privileges_on_table(self: "PostgresUtils", username: str, table: str) -> None:
        """
        Grant all privileges on the table to the user
        """
        # Grant permissions
        await self.db.execute_raw_sql(
            query=f"GRANT ALL PRIVILEGES ON TABLE {table} TO {username};",
        )
        log_info(f"Granted user {username} all privileges on table {table} successfully.")

    async def create_user_mapping_for_matomo(self: "PostgresUtils", username: str, matomo_password: str) -> None:
        """
        Create user mapping for matomo
        """
        await self.db.execute_raw_sql(
            query=f"CREATE USER MAPPING IF NOT EXISTS FOR {username} SERVER matomo_server OPTIONS  "
            f"(username 'matomo_fdw', password '{matomo_password}');",
        )
        log_info("Created user mapping for matomo database successfully.")

    async def grant_create_on_tablespace(self: "PostgresUtils", username: str, tablespace: str) -> None:
        """
        Grant create role on the given tablespace to a user
        """
        await self.db.execute_raw_sql(
            query=f"GRANT CREATE ON TABLESPACE {tablespace} TO {username};",
        )
        log_info(f"Granted user {username} create role on tablespace {tablespace} successfully.")
