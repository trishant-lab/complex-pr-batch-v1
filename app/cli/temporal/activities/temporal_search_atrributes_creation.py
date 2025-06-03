from datetime import timedelta

from temporalio import client, activity
from temporalio.api.enums.v1 import IndexedValueType
from temporalio.api.operatorservice.v1 import AddSearchAttributesRequest
from temporalio.common import RetryPolicy
from temporalio.service import RPCError

from app.cli.temporal.core.base import LaunchpadCLIBaseModel, Activity
from app.cli.temporal.core.log import log_info

from app.core.settings import AppSettings, get_settings


class TemporalSearchAttributesCreationActivityModel(LaunchpadCLIBaseModel):
    """
    TemporalNamespace dataclass
    """

    namespace: str


class TemporalSearchAttributesCreationActivity(Activity):
    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=30)

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
    @activity.defn(name="TemporalSearchAttributesCreationActivity")
    async def defn(activity_input: TemporalSearchAttributesCreationActivityModel) -> None:
        """
        Callable for the activity
        """
        # Create temporal namespace

        config: AppSettings = get_settings()

        _client = await client.Client.connect(config.temporal.dsn, namespace=activity_input.namespace)
        try:
            # Define the search attributes to be added
            search_attributes = {
                "DexitWorkflowId": IndexedValueType.INDEXED_VALUE_TYPE_KEYWORD,
                "isWaiting": IndexedValueType.INDEXED_VALUE_TYPE_BOOL,
                "EventReference": IndexedValueType.INDEXED_VALUE_TYPE_TEXT,
                "TaskStartTime": IndexedValueType.INDEXED_VALUE_TYPE_DATETIME,
                "User": IndexedValueType.INDEXED_VALUE_TYPE_KEYWORD_LIST,
                "Groups": IndexedValueType.INDEXED_VALUE_TYPE_KEYWORD_LIST,
                "TaskNumber": IndexedValueType.INDEXED_VALUE_TYPE_INT,
                "ActivityId": IndexedValueType.INDEXED_VALUE_TYPE_TEXT,
                "ActivityName": IndexedValueType.INDEXED_VALUE_TYPE_TEXT,
                "isSubWorkflow": IndexedValueType.INDEXED_VALUE_TYPE_BOOL,
                "isUserTask": IndexedValueType.INDEXED_VALUE_TYPE_BOOL,
            }

            # Upsert the search attributes
            await _client.operator_service.add_search_attributes(
                AddSearchAttributesRequest(search_attributes=search_attributes, namespace=activity_input.namespace)
            )
            log_info(f"Search attributes created for namespace {activity_input.namespace}")

        except RPCError as rpc_err:
            log_info(f"Failed to upsert search attributes: {rpc_err}")
            raise
