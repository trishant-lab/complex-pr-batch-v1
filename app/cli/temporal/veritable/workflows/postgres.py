from collections.abc import Callable
from datetime import timedelta

import pydash
from temporalio import workflow

from app.cli.temporal.core.base import Workflow
from app.cli.temporal.veritable.activities.postgres import PostgresDatabaseSetupActivity
from app.cli.veritable.common import VeritableSpec

with workflow.unsafe.imports_passed_through():
    from loguru import logger


@workflow.defn
class VeritablePostgresSetupWorkflow(Workflow):
    """
    Veritable Onboarding Workflow
    """

    @staticmethod
    def get_activities() -> list[type[Callable]]:
        """
        Return list of activities used in the workflow
        """
        return [
            PostgresDatabaseSetupActivity.defn
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", veritable: VeritableSpec) -> str | None:
        """
        Return unique workflow id from workflow input, guarantees exactly one execution of workflow
        - Add combination of one or more fields from `workflow_input` to uniquely identify workflow
        """
        return f"postgres_setup_workflow_{veritable.tenant}"

    @workflow.run
    async def run(self: "Workflow", veritable: VeritableSpec) -> None:
        """
        Entry point for workflow
        """

        try:
            logger.info(f"Starting Postgres setup for tenant: {pydash.get(veritable, 'tenant')}")
            await workflow.execute_activity(
                activity=PostgresDatabaseSetupActivity.defn,
                arg=veritable,
                retry_policy=PostgresDatabaseSetupActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
            )
            logger.info(f"Postgres setup for tenant: {pydash.get(veritable, 'tenant')} completed successfully")
        except Exception as e:
            logger.error(f"Error in postgres setup: {e}")
            raise e
