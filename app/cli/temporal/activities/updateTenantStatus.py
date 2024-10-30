from temporalio.common import RetryPolicy
from temporalio import activity, workflow


with workflow.unsafe.imports_passed_through():
    from datetime import timedelta
    from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
    from app.cli.temporal.core.log import log_error, log_info
    from app.core.db import DBManager, get_db_manager
    from app.core.settings import AppSettings, get_settings
    from app.models.tenant import TenantStatusEnum


class TenantStatus(LaunchpadCLIBaseModel):
    """
    TenantStatus dataclass
    """

    tenant_name: str
    status: str
    error_msg: None | str = None


async def update_tenant_status(
    tenant_name: str, product: str, status: TenantStatusEnum, error_message: None | str = None
) -> None:
    """
    Update tenant status in the database
    """
    config: AppSettings = get_settings()
    try:
        parameters = {
            "tenant_name": tenant_name,
            "product": product,
            "status": status.value,
            "error_message": error_message,
        }
        db: DBManager = await get_db_manager(config.postgres.dsn)
        await db.fetch_one("updateTenant.sql", db_schema_name=config.postgres.schema_name, **parameters)

        log_info(f"Tenant status updated for {tenant_name} to {status}")

    except Exception as e:
        log_error(f"Error while updating tenant status for {tenant_name}: {e}")
        raise e


class UpdateTenantStatusActivity(Activity):
    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=60)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="UpdateTenantStatusActivity")
    async def defn(activity_input: TenantStatus) -> None:
        """
        Callable for the activity
        """
        # Update tenant status
        from app.cli.temporal.jeeves.jeeves import ProductName
        from app.models.tenant import TenantStatusEnum

        status = TenantStatusEnum(activity_input.status)

        await update_tenant_status(
            tenant_name=activity_input.tenant_name,
            product=ProductName,
            status=status,
            error_message=activity_input.error_msg,
        )
