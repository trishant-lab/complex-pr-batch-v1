from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_error, log_info
from app.core.db import DBManager, get_db_manager
from app.core.ijson import ijson_dumps
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum


class SpaceStatusModel(LaunchpadCLIBaseModel):
    """
    SpaceStatus dataclass for updating space provisioning status
    """

    space_name: str
    tenant_name: str
    product: ProductEnum
    status: TenantStatusEnum
    error_msg: None | str = None


async def update_space_status(
    space_name: str,
    tenant_name: str,
    product: ProductEnum,
    status: TenantStatusEnum,
    error_message: None | str = None,
) -> None:
    """
    Update space status in the database
    """
    try:
        # Format errors as JSON
        errors_json = ijson_dumps({"error": error_message} if error_message else {})

        parameters = {
            "spacename": space_name,
            "tenant_name": tenant_name,
            "product": product.value,
            "status": status.value,
            "errors": errors_json,
        }
        db: DBManager = await get_db_manager()
        await db.fetch_one("update_space_status.sql", **parameters)

        log_info(f"Space status updated for {tenant_name}/{space_name} to {status}")

    except Exception as e:
        log_error(f"Error while updating space status for {tenant_name}/{space_name}: {e}")
        raise e


class UpdateSpaceStatusActivity(Activity):
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
    @activity.defn(name="UpdateSpaceStatusActivity")
    async def defn(activity_input: SpaceStatusModel) -> None:
        """
        Callable for the activity
        """
        await update_space_status(
            space_name=activity_input.space_name,
            tenant_name=activity_input.tenant_name,
            product=activity_input.product,
            status=activity_input.status,
            error_message=activity_input.error_msg,
        )
