import os

import orjson
import requests
from loguru import logger
from temporalio.client import Client

from app.cli.temporal.veritable.workflows.postgres import VeritablePostgresSetupWorkflow
from app.cli.veritable import TemplatePath
from app.common import generate_password
from app.core.db import DBManager, get_db_manager
from app.core.settings import ProductConfig, get_settings, AppSettings, VeritableSettings

from app.cli.postgresUtils import PostgresUtils
from app.cli.veritable.common import VeritableSpec, ProductName
from app.template_env import get_env


async def setup_supavisor_poll_user(
        db_username: str, database_name: str, db_password: str, environment: str
):
    """
    Setup supervisor poll user for veritable tenant
    """
    config: AppSettings = get_settings()

    jinja_env = get_env(template_path=TemplatePath)
    template = jinja_env.get_template(f"{environment}-supavisor-user.json")
    rendered_template = template.render(
        DATABASE=database_name,
        DB_USER=db_username,
        DB_PASSWORD=db_password
    )

    response = requests.post(
        url=f"{config.supavisor_url}/api/tenants/{db_username}",
        headers={
            "Authorization": f"Bearer {config.supavisor_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        data=orjson.loads(rendered_template)
    )

    if response.status_code < 200 or response.status_code >= 299:
        logger.error(f"Supavisor user creation failed with status code: {response.status_code}")
        raise Exception(f"Supavisor user creation failed with status code: {response.status_code}")
    logger.info(f"Supervisor poll user created: {db_username}")


async def setup_postgres(veritable: VeritableSpec):
    """
    Setup postgres database for veritable tenant
    """
    environment = os.getenv("DEPLOYMENT", "integration").lower()
    database_name = f"{ProductName}_{environment}"
    schema_name = f"{ProductName}_{veritable.tenant}"

    veritable_config: VeritableSettings = get_settings().veritable

    db_username = f"{ProductName}_{veritable.tenant}"

    try:
        db: DBManager = await get_db_manager(dsn=veritable_config.postgres.dsn)

        postgres_utils: PostgresUtils = PostgresUtils(db)

        # Check if the user already exists
        user_exists = await postgres_utils.check_if_user_exists(username=db_username)

        # generate a random password # Todo: read password from k8s secret
        password = generate_password(length=20)

        if not user_exists:
            # Create a new user in the database
            await postgres_utils.create_user(username=db_username, password=password)

        else:
            await postgres_utils.update_user_password(username=db_username, password=password)

        await setup_supavisor_poll_user(
            db_username=db_username, database_name=database_name, db_password=password, environment=environment
        )

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


async def execute_postgres_setup_workflow(veritable: VeritableSpec) -> None:
    """
    Execute the postgres setup workflow
    :param veritable:
    :return:
    """
    config: AppSettings = get_settings()
    client = await Client.connect(config.temporal.dsn, namespace=config.temporal.namespace)

    await client.execute_workflow(
        VeritablePostgresSetupWorkflow.__name__,
        veritable,
        id=VeritablePostgresSetupWorkflow.get_workflow_id(veritable=veritable),
        task_queue=config.temporal_veritable_postgres_setup_task_queue,
    )
    logger.info(f"Veritable postgres setup workflow triggered for tenant {veritable.tenant}")
