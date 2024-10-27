from temporalio.common import RetryPolicy
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from datetime import timedelta
    from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel


class TenantStatus(LaunchpadCLIBaseModel):
    """
    TenantStatus dataclass
    """

    tenant_name: str
    status: str
    error_msg: None | str = None


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
        from app.cli.activities.tenantStatus import update_tenant_status
        from app.cli.temporal.jeeves.jeeves import ProductName
        from app.models.tenant import TenantStatusEnum

        status = TenantStatusEnum(activity_input.status)

        await update_tenant_status(
            tenant_name=activity_input.tenant_name,
            product=ProductName,
            status=status,
            error_message=activity_input.error_msg,
        )
