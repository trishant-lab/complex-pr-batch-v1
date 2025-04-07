from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel


async def run_activity(
    activity: type[Activity],
    arg: LaunchpadCLIBaseModel | None,
    start_to_close_timeout: timedelta | None = None,
    retry_policy: RetryPolicy | None = None,
) -> Any:
    """
    Activity execute helper
    @param activity:
    @param arg:
    @param start_to_close_timeout:
    @param retry_policy:
    @return:
    """
    return await workflow.execute_activity(
        activity=activity.defn,
        arg=arg,
        retry_policy=retry_policy or activity.get_retry_policy(),
        start_to_close_timeout=start_to_close_timeout or activity.get_timeout(),
    )
