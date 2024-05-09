from loguru import logger

from app.core.db import DBManager


class PostgresUtils:
    """

    """
    def __init__(self, db: DBManager):
        self.db: DBManager = db

    async def create_user(self: "PostgresUtils", username: str, password: str):
        """
        Create a new user in the database
        """

        await self.db.execute_raw_sql(
            query=f"CREATE ROLE {username} NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT LOGIN PASSWORD '{password}';",
        )
        logger.info(f"User {username} created successfully")

    async def update_user_password(self: "PostgresUtils", username: str, password: str):
        """
        Update user password in the database
        """
        await self.db.execute_raw_sql(
            query=f"ALTER USER {username} WITH PASSWORD '{password}';",
        )
        logger.info(f"Password updated successfully for user {username}")

    async def create_schema(self: "PostgresUtils", schema_name: str, username: str):
        """
        Create a new schema in the database
        """
        await self.db.execute_raw_sql(
            f"CREATE SCHEMA IF NOT EXISTS { schema_name } AUTHORIZATION { username };",
        )
        logger.info(f"Schema {schema_name} created successfully")

    async def check_if_user_exists(self: "PostgresUtils", username: str):
        """
        Check if the user already exists in the database
        """
        response = await self.db.execute_raw_sql(
            f"SELECT usename FROM pg_user WHERE usename = '{username}'",
        )
        logger.info(f"User {username} exists: {response}")
        return response

    async def grant_user_to_connect_and_create(self: "PostgresUtils", username: str, database: str):

        # Grant permissions
        await self.db.execute_raw_sql(
            query=f"GRANT CONNECT, CREATE ON DATABASE {database} TO {username};",
        )

    async def grant_user_all_privileges_on_schema(self: "PostgresUtils", username: str, schema_name: str):
        # Grant permissions
        await self.db.execute_raw_sql(
            query=f"GRANT ALL ON SCHEMA {schema_name} TO {username}",
        )
