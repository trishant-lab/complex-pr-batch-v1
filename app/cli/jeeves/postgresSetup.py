from loguru import logger

from app.cli.temporal.core.log import log_info
from app.onepasswordutil import OnePasswordUtil
from app.cli.jeeves.jeeves import JeevesSpec, ProductName
from app.cli.postgresUtils import PostgresUtils
from app.common import generate_password
from app.core.db import DBManager, get_db_manager
from app.core.settings import get_settings, JeevesSettings


async def setup_postgres(jeeves: JeevesSpec) -> None:
    """
    Setup postgres database for jeeves tenant
    """
    database_name = f"{ProductName}"
    schema_name = jeeves.tenant

    jeeves_config: JeevesSettings = get_settings().jeeves

    db_username = f"{ProductName}_{jeeves.tenant}"

    try:
        db: DBManager = await get_db_manager(dsn=jeeves_config.postgres.dsn)

        postgres_utils: PostgresUtils = PostgresUtils(db)

        # Check if the user already exists
        user_exists = await postgres_utils.check_if_user_exists(username=db_username)

        password = generate_password(length=20)

        if not user_exists:
            # Create a new user in the database
            await postgres_utils.create_user(username=db_username, password=password)

        else:
            await postgres_utils.update_user_password(username=db_username, password=password)

        OnePasswordUtil(
            tenant=f"Jeeves_{jeeves.tenant}",
            server_item="application-config",
            vault="Jeeves",
        ).create_or_replace("pg_password", password)

        # Create schema in the database
        await postgres_utils.create_schema(schema_name=schema_name, username=db_username)

        # Grant user to connect and create on database
        await postgres_utils.grant_user_to_connect_and_create(username=db_username, database=database_name)

        # Grant ALL privileges on tenant schema
        await postgres_utils.grant_user_all_privileges_on_schema(username=db_username, schema_name=schema_name)

        # Grant ALL privileges on public schema
        await postgres_utils.grant_user_all_privileges_on_schema(username=db_username, schema_name="public")

        await postgres_utils.create_user_mapping_for_keycloak(
            username=db_username, keycloak_password=jeeves_config.keycloak_db_password
        )

        await postgres_utils.grant_user_all_privileges_on_table(table="user_entity", username=db_username)
        await postgres_utils.grant_user_all_privileges_on_table(table="keycloak_role", username=db_username)
        await postgres_utils.grant_user_all_privileges_on_table(table="user_role_mapping", username=db_username)
        await postgres_utils.grant_user_all_privileges_on_table(table="realm", username=db_username)

        await postgres_utils.create_user_mapping_for_matomo(
            username=db_username, matomo_password=jeeves_config.matomo_db_password
        )

        await postgres_utils.grant_user_all_privileges_on_table(table="matomo_log_visit", username=db_username)
        await postgres_utils.grant_user_all_privileges_on_table(table="matomo_log_action", username=db_username)
        await postgres_utils.grant_user_all_privileges_on_table(table="matomo_log_media", username=db_username)
        await postgres_utils.grant_user_all_privileges_on_table(
            table="matomo_log_link_visit_action", username=db_username
        )

        await postgres_utils.grant_user_all_privileges_on_table(table="matomo_log_visit_view", username=db_username)
        await postgres_utils.grant_user_all_privileges_on_table(table="matomo_log_action_view", username=db_username)
        await postgres_utils.grant_user_all_privileges_on_table(table="matomo_log_media_view", username=db_username)
        await postgres_utils.grant_user_all_privileges_on_table(
            table="matomo_log_link_visit_action_view", username=db_username
        )

        log_info(f"Postgres setup for tenant {jeeves.tenant} completed successfully")

        return
    except Exception as e:
        logger.error(f"Error in postgres database setup: {e}")
        raise e
