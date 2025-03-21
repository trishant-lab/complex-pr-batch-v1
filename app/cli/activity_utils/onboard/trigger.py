from app.cli.temporal.models.onboard import CustomerWorkflowInput
from app.core.cli_settings import WorkerQueues
from app.core.db import DBManager, get_db_manager
from app.models.tenant import TenantStatusEnum


async def trigger_onboarding_workflow(activity_input: CustomerWorkflowInput) -> None:
    """
    Update provisioning status as process & trigger onboard workflow
    """
    from app.cli.temporal.starter import trigger_workflow
    from app.cli.temporal.workflows.onboard import OnboardWorkflow

    db: DBManager = await get_db_manager()
    await db.execute(
        "put.sql",
        table="operatorstatus",
        payload={"status": TenantStatusEnum.Provisioning},
        where=f"customerid='{activity_input.customer_id!s}'",
    )
    await trigger_workflow(
        workflow=OnboardWorkflow,
        workflow_input=activity_input,
        queue=WorkerQueues.onboard,
    )
