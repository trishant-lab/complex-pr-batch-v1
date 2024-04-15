import uuid
from dataclasses import dataclass

from loguru import logger
from temporalio import activity

from app.core.db import DBManager, get_db_manager
from app.core.settings import get_settings, ProductConfig
from app.temporalworkflows.onepasswordutil import OnePasswordUtil


@dataclass
class GenerateRandomPasswordActivityInput:
    product: str
    tenant: str


@activity.defn
async def generate_random_password(activity_input: GenerateRandomPasswordActivityInput) -> None:
    """
    :return:
    """
    product_config: ProductConfig = get_settings().product_config[activity_input.product.lower()]

    # generate a random password
    password = uuid.uuid4().hex.replace("-", "")[20]

    # store the password in 1password
    OnePasswordUtil(
        tenant=activity_input.tenant,
        vault=product_config.vault_name,
        server_item=product_config.server_item
    ).insert_if_not_exists(
        key="postgres_database_password",
        value=password
    )


@dataclass
class CreateDatabaseUserActivityInput:
    product: str
    username: str
    tenant: str


@activity.defn
async def create_user_activity(activity_input: CreateDatabaseUserActivityInput) -> None:
    """
    :return:
    """
    product_config: ProductConfig = get_settings().product_config[activity_input.product.lower()]

    db: DBManager = await get_db_manager(dsn=product_config.postgres_dsn)

    # Check if the user already exists
    try:
        response = await db.fetch_one(
            "PostgresDatabaseSetup/checkIfUserExitInDatabase.sql",
            username=f"{activity_input.username}"
        )
    except Exception as e:
        logger.error(f"Error while checking if user exists: {e}")
        raise e

    if response:
        logger.info(f"User {activity_input.username} already exists")
        return

    # get the password from 1password
    password = OnePasswordUtil(
        tenant=activity_input.tenant,
        vault=product_config.vault_name,
        server_item=product_config.one_password_server_item
    ).get_key("postgres_database_password")

    try:
        parameters = {
            "username": activity_input.username,
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
    logger.info(f"User {activity_input.username} created successfully")
    return


@dataclass
class CreateDatabaseSchemaActivityInput:
    product: str
    db_username: str
    tenant_name: str
    database_name: str


@activity.defn
async def create_schema_activity(activity_input: CreateDatabaseSchemaActivityInput) -> None:
    """
    :return:
    """
    product_config: ProductConfig = get_settings().product_config[activity_input.product.lower()]

    db: DBManager = await get_db_manager(dsn=product_config.postgres_dsn)
    try:
        # Create a new schema
        parameters = {
            "username": activity_input.db_username,
            "schema_name": activity_input.tenant_name,
            "database": activity_input.database_name
        }
        await db.execute(
            "PostgresDatabaseSetup/createSchemaInDatabase.sql",
            **parameters
        )
    except Exception as e:
        logger.error(f"Error while creating schema: {e}")
        raise e
    logger.info(f"Schema {activity_input.db_username} created successfully")
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


@dataclass
class GrantPermissionsActivityInput:
    db_username: str
    tenant_name: str
    database_name: str
    product: str


@activity.defn
async def grant_permissions_activity(activity_input: GrantPermissionsActivityInput) -> None:
    """
    :return:
    """
    product_config: ProductConfig = get_settings().product_config[activity_input.product.lower()]
    db: DBManager = await get_db_manager(dsn=activity_input.product)

    # Grant user to connect and create on database
    await grant_user_to_connect_and_create_on_database(db, activity_input.db_username, activity_input.database_name)

    # Grant ALL privileges on tenant schema
    await grant_user_to_all_privileges_on_schema(db, activity_input.db_username, activity_input.tenant_name)

    # Grant ALL privileges on public schema
    await grant_user_to_all_privileges_on_schema(db, activity_input.db_username, "public")
    return
