from datetime import datetime
from loguru import logger
import orjson
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

    # In penknife we are not creating tenant based user
    db_username = f"{ProductName}"

    try:
        db: DBManager = await get_db_manager(dsn=penknife_config.postgres.dsn)

        postgres_utils: PostgresUtils = PostgresUtils(db)

        await postgres_utils.create_schema(schema_name=schema_name, username=db_username)

        await postgres_utils.grant_user_all_privileges_on_schema(username=db_username, schema_name=schema_name)

        log_info(f"Postgres setup for tenant {penknife.tenant} completed successfully")

        return
    except Exception as e:
        logger.error(f"Error in postgres database setup: {e}")
        raise e
    
async def add_user_mapping(penknife: PenknifeSpec, keycloak_user_id: str, novu_subscriber_id: str) -> None:
    """
    Update useraudit entry for the new tenant
    """
    schema_name = penknife.tenant

    penknife_config: PenknifeSettings = get_settings().penknife
    
    try:
        db: DBManager = await get_db_manager(dsn=penknife_config.postgres.dsn)

        attributes = orjson.dumps({"email": penknife.email}).decode("utf-8")
        db.execute_raw_sql(f"INSERT INTO {schema_name}.subscriptionmapping (keycloakuserid, subscriberid, attributes) VALUES ($${keycloak_user_id}$$, $${novu_subscriber_id}$$, $${attributes}$$);")
        db.execute_raw_sql(f"""INSERT INTO {schema_name}.useraudit ("user", creationdate, enabled, needemailscope, hideuseremails) VALUES ($${penknife.email}$$, $${datetime.now()}$$, true, false, false);""")

        log_info("User detail is added to postgres")
        return
    
    except Exception as e:
        logger.error(f"Error while updating user entry in useraudit: {e}")
        raise e
