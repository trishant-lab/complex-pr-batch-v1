from temporalio import client
from temporalio.api.enums.v1 import IndexedValueType
from temporalio.api.operatorservice.v1 import AddSearchAttributesRequest
from temporalio.service import RPCError

from app.cli.temporal.core.log import log_info

from app.core.settings import AppSettings, get_settings


class TemporalSearchAttributesCreation:
    def __init__(self: "TemporalSearchAttributesCreation", namespace: str) -> None:
        """
        Constructor
        """
        self.config: AppSettings = get_settings()
        self.namespace = namespace

    async def create_search_attributes(self: "TemporalSearchAttributesCreation") -> None:
        """
        Create Search Attributes for the Temporal namespace
        """
        _client = await client.Client.connect(self.config.temporal.dsn, namespace=self.namespace)
        try:
            # Define the search attributes to be added
            search_attributes = {
                "DexitWorkflowId": IndexedValueType.INDEXED_VALUE_TYPE_KEYWORD,
                "isWaiting": IndexedValueType.INDEXED_VALUE_TYPE_BOOL,
                "EventReference": IndexedValueType.INDEXED_VALUE_TYPE_TEXT,
                "TaskStartTime": IndexedValueType.INDEXED_VALUE_TYPE_DATETIME,
                "User": IndexedValueType.INDEXED_VALUE_TYPE_KEYWORD_LIST,
            }

            # Upsert the search attributes
            await _client.operator_service.add_search_attributes(
                AddSearchAttributesRequest(search_attributes=search_attributes, namespace=self.namespace)
            )
            log_info(f"Search attributes created for namespace {self.namespace}")

        except RPCError as rpc_err:
            log_info(f"Failed to upsert search attributes: {rpc_err}")
            raise
