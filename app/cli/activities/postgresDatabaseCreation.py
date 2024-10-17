from typing import Any
from app.cli.postgresUtils import PostgresUtils
from app.common import generate_password
from app.core.db import get_db_manager, DBManager
from app.cli.temporal.core.log import log_info


async def setup_postgres_database(
    product_name: str,
    database_name: str,
    db_username: str,
    vault_name: str,
    config: Any,
) -> None:
    """
    Setup postgres database for tenant
    """
    db: DBManager = await get_db_manager(dsn=config.postgres.dsn)

    postgres_utils: PostgresUtils = PostgresUtils(db)

    password = generate_password(length=20)

    await postgres_utils.create_database(database_name=database_name)

    user_exists = await postgres_utils.check_if_user_exists(username=db_username)
    log_info(f"User {db_username} exists: {user_exists}")

    if not user_exists:
        await postgres_utils.create_user(username=db_username, password=password)
    else:
        await postgres_utils.update_user_password(username=db_username, password=password)

    await postgres_utils.grant_user_to_connect_and_create(db_username=db_username, database_name=database_name)
