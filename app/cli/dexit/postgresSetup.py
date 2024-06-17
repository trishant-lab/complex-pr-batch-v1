from loguru import logger

from app.cli.dexit.secretSetup import Secret
from app.cli.dexit.dexit import DexitSpec, ProductName
from app.cli.postgresUtils import PostgresUtils
from app.common import generate_password
from app.core.db import DBManager, get_db_manager
from app.core.settings import get_settings, DexitSettings


def create_k8s_postgres_secret(dexit: DexitSpec, password: str) -> None:
    """
    Create a secret in k8s for the postgres password
    """
    Secret(dexit=dexit, name="dexit-postgres-password", string_data={"POSTGRES_PASSWORD": password}).put()


async def setup_postgres(dexit: DexitSpec) -> None:
    """
    Setup postgres database for dexit tenant
    """
    database_name = f"{ProductName}"
    schema_name = dexit.tenant

    dexit_config: DexitSettings = get_settings().dexit

    db_username = f"{ProductName}_{dexit.tenant}"

    try:
        db: DBManager = await get_db_manager(dsn=dexit_config.postgres.dsn)

        postgres_utils: PostgresUtils = PostgresUtils(db)

        # Check if the user already exists
        user_exists = await postgres_utils.check_if_user_exists(username=db_username)

        password = generate_password(length=20)

        # Create a secret in k8s for the postgres password
        create_k8s_postgres_secret(dexit=dexit, password=password)

        if not user_exists:
            # Create a new user in the database
            await postgres_utils.create_user(username=db_username, password=password)

        else:
            await postgres_utils.update_user_password(username=db_username, password=password)

        # Create schema in the database
        await postgres_utils.create_schema(schema_name=schema_name, username=db_username)

        # Grant user to connect and create on database
        await postgres_utils.grant_user_to_connect_and_create(username=db_username, database=database_name)

        # Grant ALL privileges on tenant schema
        await postgres_utils.grant_user_all_privileges_on_schema(username=db_username, schema_name=schema_name)

        # Grant ALL privileges on public schema
        await postgres_utils.grant_user_all_privileges_on_schema(username=db_username, schema_name="public")

        await postgres_utils.create_user_mapping_for_keycloak(
            username=db_username, keycloak_password=dexit_config.keycloak_db_password
        )

        await postgres_utils.grant_user_all_privileges_on_table(table="user_entity", username=db_username)
        await postgres_utils.grant_user_all_privileges_on_table(table="keycloak_role", username=db_username)
        await postgres_utils.grant_user_all_privileges_on_table(table="user_role_mapping", username=db_username)
        await postgres_utils.grant_user_all_privileges_on_table(table="user_attribute", username=db_username)
        # await postgres_utils.grant_user_all_privileges_on_table(table="realm", username=db_username)

        await postgres_utils.create_user_mapping_for_matomo(
            username=db_username, matomo_password=dexit_config.matomo_db_password
        )

        await postgres_utils.grant_user_all_privileges_on_table(table="matomo_log_visit", username=db_username)
        await postgres_utils.grant_user_all_privileges_on_table(table="matomo_log_action", username=db_username)
        await postgres_utils.grant_user_all_privileges_on_table(table="matomo_log_media", username=db_username)
        await postgres_utils.grant_user_all_privileges_on_table(
            table="matomo_log_link_visit_action", username=db_username
        )

        return
    except Exception as e:
        logger.error(f"Error in postgres database setup: {e}")
        raise e
