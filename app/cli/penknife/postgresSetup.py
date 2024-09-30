from loguru import logger
from app.cli.penknife.models.penknifespec import PenknifeSpec
from app.cli.penknife.penknife import ProductName
from app.cli.postgresUtils import PostgresUtils
from app.cli.temporal.core.log import log_info
from app.common import generate_password
from app.core.db import DBManager, get_db_manager
from app.core.settings import PenknifeSettings, get_settings
from app.onepasswordutil import OnePasswordUtil


async def setup_postgres(penknife: PenknifeSpec) -> None:
    """
    Setup postgres database for penknife tenant
    """
    database_name = f"{ProductName}"
    schema_name = penknife.tenant

    penknife_config: PenknifeSettings = get_settings().penknife

    db_username = f"{ProductName}_{penknife.tenant}"

    try:
        db: DBManager = await get_db_manager(dsn=penknife_config.postgres.dsn)

        postgres_utils: PostgresUtils = PostgresUtils(db)

        user_exists = await postgres_utils.check_if_user_exists(username=db_username)

        password = generate_password(length=20)

        if not user_exists:
            await postgres_utils.create_user(username=db_username, password=password)

        else:
            await postgres_utils.update_user_password(username=db_username, password=password)

        OnePasswordUtil(
            tenant=f"PENKNIFE_{penknife.tenant}",
            server_item="application-config",
            vault="Penknife",
        ).create_or_replace("pg_password", password)

        await postgres_utils.create_schema(schema_name=schema_name, username=db_username)

        await postgres_utils.grant_user_to_connect_and_create(username=db_username, database=database_name)

        await postgres_utils.grant_user_all_privileges_on_schema(username=db_username, schema_name=schema_name)

        await postgres_utils.grant_user_all_privileges_on_schema(username=db_username, schema_name="public")

        await postgres_utils.create_user_mapping_for_keycloak(
            username=db_username, keycloak_password=penknife_config.keycloak_db_password
        )

        await postgres_utils.grant_user_all_privileges_on_table(table="user_entity", username=db_username)
        await postgres_utils.grant_user_all_privileges_on_table(table="realm", username=db_username)

        # Not in use
        # await postgres_utils.grant_user_all_privileges_on_table(table="keycloak_role", username=db_username)
        # await postgres_utils.grant_user_all_privileges_on_table(table="user_role_mapping", username=db_username)

        log_info(f"Postgres setup for tenant {penknife.tenant} completed successfully")

        return
    except Exception as e:
        logger.error(f"Error in postgres database setup: {e}")
        raise e