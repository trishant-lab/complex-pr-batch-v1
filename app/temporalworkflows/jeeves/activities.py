import uuid
from loguru import logger
from temporalio import activity

from app.core.db import DBManager, get_db_manager
from app.core.settings import ProductConfig, AppSettings, get_settings


async def generate_random_password(length) -> str:
    """
    :return:
    """
    password = uuid.uuid4().hex.replace("-", "")[length]
    return password


class CreateDatabaseUserActivityInput:
    username: str
    password: str
    postgres_dsn: str


async def create_user_activity(postgres_dsn: str, username: str, password: str) -> None:
    """
    :return:
    """
    db: DBManager = await get_db_manager(dsn=postgres_dsn)

    # Check if the user already exists
    try:
        response = await db.fetch_one(
            "PostgresDatabaseSetup/checkIfUserExitInDatabase.sql",
            username=f"{username}"
        )
    except Exception as e:
        logger.error(f"Error while checking if user exists: {e}")
        raise e

    if response:
        logger.info(f"User {username} already exists")
        return

    try:
        parameters = {
            "username": username,
            "password": password
        }
        # Create a new user
        await db.execute(
            "PostgresDatabaseSetup/createUserInDatabase.sql",
            **parameters
        )
    except Exception as e:
        logger.error(f"Error while creating user: {e}")
        raise e
    logger.info(f"User {username} created successfully")
    return


async def create_schema_activity(postgres_dsn: str, username: str, database: str, schema_name: str) -> None:
    """
    :return:
    """
    db: DBManager = await get_db_manager(dsn=postgres_dsn)
    try:
        # Create a new schema
        parameters = {
            "username": username,
            "schema_name": schema_name,
            "database": database
        }
        await db.execute(
            "PostgresDatabaseSetup/createSchemaInDatabase.sql",
            **parameters
        )
    except Exception as e:
        logger.error(f"Error while creating schema: {e}")
        raise e
    logger.info(f"Schema {username} created successfully")
    return


async def grant_user_to_connect_and_create_on_database(db: DBManager, user_name: str, database_name: str):
    try:
        # Grant permissions
        parameters = {
            "username": user_name,
            "database": database_name
        }
        await db.execute(
            "PostgresDatabaseSetup/grantUserToConnectAndCreateOnDatabase.sql",
            **parameters
        )
    except Exception as e:
        logger.error(f"Error while granting permissions: {e}")
        raise e
    logger.info(f"Permissions granted to {user_name} successfully")
    return


async def grant_user_to_all_privileges_on_schema(db: DBManager, user_name: str, schema_name: str):
    try:
        # Grant permissions
        parameters = {
            "username": user_name,
            "schema_name": schema_name
        }
        await db.execute(
            "PostgresDatabaseSetup/grantUserToAllPrivilegesOnSchema.sql",
            **parameters
        )
    except Exception as e:
        logger.error(f"Error while granting permissions: {e}")
        raise e
    logger.info(f"Permissions granted to {user_name} successfully")
    return


async def grant_permissions_activity(postgres_dsn: str, user_name: str, database: str, schema_name: str) -> None:
    """
    :return:
    """
    db: DBManager = await get_db_manager(dsn=postgres_dsn)

    # Grant user to connect and create on database
    await grant_user_to_connect_and_create_on_database(db, user_name, database)

    # Grant ALL privileges on tenant schema
    await grant_user_to_all_privileges_on_schema(db, user_name, schema_name)

    # Grant ALL privileges on public schema
    await grant_user_to_all_privileges_on_schema(db, user_name, "public")
    return


class DSLActivities:
    @activity.defn
    async def postgres_setup_activity(self, payload: dict) -> None:

        config: AppSettings = get_settings()

        product_config: ProductConfig = config.product_config[payload['product'].lower()]

        db_username = f"{payload['product']}_{payload['tenant']}"
        password = await generate_random_password(20)
        await create_user_activity(postgres_dsn=product_config.postgres.dsn, username=db_username, password=password)

        await create_schema_activity(
            postgres_dsn=product_config.postgres.dsn,
            username=db_username,
            database=product_config.postgres.db,
            schema_name=payload['tenant']
        )

        await grant_permissions_activity(
            postgres_dsn=product_config.postgres.dsn,
            user_name=db_username,
            database=product_config.postgres.db,
            schema_name=payload['tenant']
        )

    @activity.defn
    async def keycloak_setup_activity(self, arg: str) -> str:
        print(arg)
        return "keycloak_setup_activity"
