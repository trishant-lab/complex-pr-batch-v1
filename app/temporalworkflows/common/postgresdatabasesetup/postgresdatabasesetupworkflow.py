from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

from app.core.settings import AppSettings, get_settings, ProductConfig
from app.temporalworkflows.common.postgresdatabasesetup.postgresdatabasesetupactivity import (
    create_user_activity, CreateDatabaseUserActivityInput, generate_random_password,
    GenerateRandomPasswordActivityInput, create_schema_activity, CreateDatabaseSchemaActivityInput,
    grant_permissions_activity, GrantPermissionsActivityInput
)


@dataclass
class PostgresDatabaseSetupWorkflowInput:
    product: str
    tenant: str
    env: str
    database_name: str
    schema_name: str


@workflow.defn(name="postgresdatabasesetup_workflow", sandboxed=False)
class PostgresDatabaseSetupWorkflow:
    @workflow.run
    async def run(self, workflow_input: PostgresDatabaseSetupWorkflowInput) -> None:
        """
        :return:
        """
        retry_policy: RetryPolicy = RetryPolicy(
            backoff_coefficient=2.0,
            maximum_attempts=1,
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=60),
        )

        # config: AppSettings = get_settings()

        # product_config: ProductConfig = config.product_config[workflow_input.product.lower()]

        # Generate a random password
        await workflow.execute_activity(
            generate_random_password,
            GenerateRandomPasswordActivityInput(
                product=workflow_input.product,
                tenant=workflow_input.tenant,
            ),
            retry_policy=retry_policy,
            start_to_close_timeout=timedelta(seconds=30)
        )

        db_username = f"{workflow_input.product.lower()}_{workflow_input.tenant.lower()}"

        # Create a new user in the database
        await workflow.execute_activity(
            create_user_activity,
            CreateDatabaseUserActivityInput(
                username=db_username,
                product=workflow_input.product,
                tenant=workflow_input.tenant
            ),
            retry_policy=retry_policy,
            start_to_close_timeout=timedelta(seconds=60)
        )

        # Create schema in the database with the new user
        await workflow.execute_activity(
            create_schema_activity,
            CreateDatabaseSchemaActivityInput(
                db_username=db_username,
                schema_name=workflow_input.schema_name,
                database_name=workflow_input.database_name,
                product=workflow_input.product
            ),
            retry_policy=retry_policy,
            start_to_close_timeout=timedelta(seconds=60)
        )

        # Grant permissions to the new user
        await workflow.execute_activity(
            grant_permissions_activity,
            GrantPermissionsActivityInput(
                db_username=db_username,
                schema_name=workflow_input.schema_name,
                database_name=workflow_input.database_name,
                product=workflow_input.product
            ),
            retry_policy=retry_policy,
            start_to_close_timeout=timedelta(seconds=60)
        )

