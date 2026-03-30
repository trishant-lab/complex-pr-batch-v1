from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_error, log_info
from app.core.db import DBManager, get_db_manager
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum


class TenantCliStatus(LaunchpadCLIBaseModel):
    """
    TenantStatus dataclass
    """

    tenant_name: str
    product: ProductEnum
    status: TenantStatusEnum
    error_msg: None | str = None
    space_name: str | None = None


async def update_tenant_status(
    tenant_name: str,
    product: ProductEnum,
    status: TenantStatusEnum,
    error_message: None | str = None,
    space_name: str | None = None,
) -> None:
    """
    Update tenant status in the database
    """
    try:
        parameters = {
            "tenant_name": tenant_name,
            "product": product.value,
            "status": status.value,
            "error_message": error_message,
            "spacename": space_name,
        }
        db: DBManager = await get_db_manager()
        await db.fetch_one("update_tenant.sql", **parameters)

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
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="UpdateTenantStatusActivity")
    async def defn(activity_input: TenantCliStatus) -> None:
        """
        Callable for the activity
        """
        # Update tenant status
        from app.models.tenant import TenantStatusEnum

        status = TenantStatusEnum(activity_input.status)

        await update_tenant_status(
            tenant_name=activity_input.tenant_name,
            product=activity_input.product,
            status=status,
            error_message=activity_input.error_msg,
            space_name=activity_input.space_name,
        )
