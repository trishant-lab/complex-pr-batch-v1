from typing import Any

from loguru import logger

import os
import requests

from app.cli.temporal.core.log import log_info
from app.onepasswordutil import OnePasswordUtil
from app.cli.postgresUtils import PostgresUtils
from app.common import generate_password
from app.core.db import DBManager, get_db_manager
from app.core.settings import get_settings, AppSettings
from app.template_env import get_env


async def setup_supavisor_poll_user(
    db_username: str, database_name: str, db_password: str, environment: str, template_path: str
) -> None:
    """
    Setup supervisor poll user for tenant
    """
    config: AppSettings = get_settings()

    jinja_env = get_env(template_path=template_path)
    template = jinja_env.get_template(f"{environment}-supavisor-user.json")
    rendered_template = template.render(DATABASE=database_name, DB_USER=db_username, DB_PASSWORD=db_password)

    response = requests.put(
        url=f"{config.supavisor_url}/api/tenants/{db_username}",
        headers={
            "Authorization": f"Bearer {config.supavisor_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        data=rendered_template,
        timeout=120,
    )

    if response.status_code < 200 or response.status_code >= 299:
        logger.error(f"Supavisor user creation failed with status code: {response.status_code}")
        raise Exception(f"Supavisor user creation failed with status code: {response.status_code}")
    logger.info(f"Supervisor poll user created: {db_username}")


async def setup_postgres(
    tenant: str,
    product_name: str,
    schema_name: str,
    database_name: str,
    vault_name: str,
    template_path: str,
    config: Any,
    keycloak_db: bool = False,
    matomo_db: bool = False,
) -> None:
    """
    Setup postgres database for tenant
    """
    environment = os.getenv("DEPLOYMENT", "integration").lower()

    db_username = f"{database_name.lower()}_{tenant}"

    try:
        db: DBManager = await get_db_manager(dsn=config.postgres.dsn)

        postgres_utils: PostgresUtils = PostgresUtils(db)

        # Check if the user already exists
        user_exists = await postgres_utils.check_if_user_exists(username=db_username)
        log_info(f"User {db_username} exists: {user_exists}")

        password = generate_password(length=20)

        if not user_exists:
            # Create a new user in the database
            log_info(f"Creating user {db_username} in the database")
            await postgres_utils.create_user(username=db_username, password=password)

        else:
            await postgres_utils.update_user_password(username=db_username, password=password)

        OnePasswordUtil(
            tenant=f"{product_name}_{tenant}",
            server_item="application-config",
            vault=vault_name,
        ).create_or_replace("pg_password", password)

        await setup_supavisor_poll_user(
            db_username=db_username,
            database_name=database_name,
            db_password=password,
            environment=environment,
            template_path=template_path,
        )

        # Create schema in the database
        await postgres_utils.create_schema(schema_name=schema_name, username=db_username)

        # Grant user to connect and create on database
        await postgres_utils.grant_user_to_connect_and_create(username=db_username, database=database_name)

        # Grant ALL privileges on tenant schema
        await postgres_utils.grant_user_all_privileges_on_schema(username=db_username, schema_name=schema_name)

        # Grant ALL privileges on public schema
        await postgres_utils.grant_user_all_privileges_on_schema(username=db_username, schema_name="public")

        if keycloak_db:
            await postgres_utils.create_user_mapping_for_keycloak(
                username=db_username, keycloak_password=config.keycloak_db_password
            )

            await postgres_utils.grant_user_all_privileges_on_table(table="user_entity", username=db_username)
            await postgres_utils.grant_user_all_privileges_on_table(table="keycloak_role", username=db_username)
            await postgres_utils.grant_user_all_privileges_on_table(table="user_role_mapping", username=db_username)
            await postgres_utils.grant_user_all_privileges_on_table(table="user_attribute", username=db_username)
            await postgres_utils.grant_user_all_privileges_on_table(table="realm", username=db_username)

        if matomo_db:
            await postgres_utils.create_user_mapping_for_matomo(
                username=db_username, matomo_password=config.matomo_db_password
            )

            await postgres_utils.grant_user_all_privileges_on_table(table="matomo_log_visit", username=db_username)
            await postgres_utils.grant_user_all_privileges_on_table(table="matomo_log_action", username=db_username)
            await postgres_utils.grant_user_all_privileges_on_table(table="matomo_log_media", username=db_username)
            await postgres_utils.grant_user_all_privileges_on_table(
                table="matomo_log_link_visit_action", username=db_username
            )
            await postgres_utils.grant_user_all_privileges_on_table(table="matomo_log_visit_view", username=db_username)
            await postgres_utils.grant_user_all_privileges_on_table(
                table="matomo_log_action_view", username=db_username
            )
            await postgres_utils.grant_user_all_privileges_on_table(table="matomo_log_media_view", username=db_username)
            await postgres_utils.grant_user_all_privileges_on_table(
                table="matomo_log_link_visit_action_view", username=db_username
            )

        log_info(f"Postgres setup for tenant {tenant} completed successfully")

        return
    except Exception as e:
        logger.error(f"Error in postgres database setup: {e}")
        raise e
