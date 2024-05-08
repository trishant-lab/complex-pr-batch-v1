import os

from loguru import logger

from app.common import generate_password
from app.core.db import DBManager, get_db_manager
from app.core.settings import ProductConfig, get_settings

from app.onepasswordutil import OnePasswordUtil
from app.temporal.common.postgresUtils import PostgresUtils
from app.temporal.veritable.utils.common import VeritableSpec, ProductName, OnepasswordVaultName, OnepasswordItemName


async def setup_postgres(veritable: VeritableSpec):
    """
    Setup postgres database for veritable tenant
    """
    environment = os.getenv("DEPLOYMENT", "integration").lower()
    database_name = f"{ProductName}_{environment}"
    schema_name = f"{ProductName}_{veritable.tenant}"

    product_config: ProductConfig = get_settings().product_config[ProductName]

    db_username = f"{ProductName}_{veritable.tenant}"

    try:
        db: DBManager = await get_db_manager(dsn=product_config.postgres.dsn)

        postgres_utils: PostgresUtils = PostgresUtils(db)

        # Check if the user already exists
        user_exists = await postgres_utils.check_if_user_exists(username=db_username)

        if not user_exists:
            # generate a random password
            password = generate_password(length=20)

            # Create a new user in the database
            await postgres_utils.create_user(username=db_username, password=password)
            # store the password in 1password
            OnePasswordUtil(
                tenant=veritable.tenant,
                vault=OnepasswordVaultName,
                server_item=OnepasswordItemName.format(environment=environment)
            ).create_or_replace(key="postgres_database_password", value=password)

        else:
            logger.info(f"User {db_username} already exists in the database")

        # Create schema in the database
        await postgres_utils.create_schema(schema_name=schema_name, username=db_username)

        # Grant user to connect and create on database
        await postgres_utils.grant_user_to_connect_and_create(username=db_username, database=database_name)

        # Grant ALL privileges on tenant schema
        await postgres_utils.grant_user_all_privileges_on_schema(username=db_username, schema_name=schema_name)

        # Grant ALL privileges on public schema
        await postgres_utils.grant_user_all_privileges_on_schema(username=db_username, schema_name="public")
        return
    except Exception as e:
        logger.error(f"Error in postgres database setup: {e}")
        raise e
