from loguru import logger

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
        logger.info(f"User {username} created successfully")

    async def update_user_password(self: "PostgresUtils", username: str, password: str) -> None:
        """
        Update user password in the database
        """
        await self.db.execute_raw_sql(
            query=f"ALTER USER {username} WITH PASSWORD '{password}';",
        )
        logger.info(f"Password updated successfully for user {username}")

    async def create_schema(self: "PostgresUtils", schema_name: str, username: str) -> None:
        """
        Create a new schema in the database
        """
        await self.db.execute_raw_sql(
            f"CREATE SCHEMA IF NOT EXISTS { schema_name } AUTHORIZATION { username };",
        )
        logger.info(f"Schema {schema_name} created successfully")

    async def check_if_user_exists(self: "PostgresUtils", username: str) -> None:
        """
        Check if the user already exists in the database
        """
        response = await self.db.fetch_one(
            sqlfile="checkIfUserExists.sql",
            username=username,
        )
        logger.info(f"User {username} exists: {response}")
        return response

    async def grant_user_to_connect_and_create(self: "PostgresUtils", username: str, database: str) -> None:
        """
        Grant user to connect and create on the database
        """
        # Grant permissions
        await self.db.execute_raw_sql(
            query=f"GRANT CONNECT, CREATE ON DATABASE {database} TO {username};",
        )

    async def grant_user_all_privileges_on_schema(self: "PostgresUtils", username: str, schema_name: str) -> None:
        """
        Grant all privileges on the schema to the user
        """
        # Grant permissions
        await self.db.execute_raw_sql(
            query=f"GRANT ALL ON SCHEMA {schema_name} TO {username}",
        )

    async def create_user_mapping_for_keycloak(self: "PostgresUtils", username: str, keycloak_password: str) -> None:
        """
        Create user mapping for keycloak
        """
        await self.db.execute_raw_sql(
            query=f"CREATE USER MAPPING IF NOT EXISTS FOR {username} SERVER keycloak_server OPTIONS  "
            f"(user 'keyclock_fdw', password '{keycloak_password}');",
        )
        logger.info(f"User mapping created successfully for user {username}")

    async def grant_user_all_privileges_on_table(self: "PostgresUtils", username: str, table: str) -> None:
        """
        Grant all privileges on the table to the user
        """
        # Grant permissions
        await self.db.execute_raw_sql(
            query=f"GRANT ALL PRIVILEGES ON TABLE {table} TO {username};",
        )

    async def create_user_mapping_for_matomo(self: "PostgresUtils", username: str, matomo_password: str) -> None:
        """
        Create user mapping for matomo
        """
        await self.db.execute_raw_sql(
            query=f"CREATE USER MAPPING IF NOT EXISTS FOR {username} SERVER matomo_server OPTIONS  "
            f"(username 'matomo_fdw', password '{matomo_password}');",
        )
        logger.info(f"User mapping created successfully for user {username}")
