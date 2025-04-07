import async_lru
from google.protobuf.duration_pb2 import Duration
from loguru import logger
from temporalio import client
from temporalio.api.workflowservice.v1 import RegisterNamespaceRequest
from temporalio.converter import DataConverter
from temporalio.service import RPCError, RPCStatusCode

from app.cli.temporal.core.data_converter import PydanticPayloadConverter
from app.core.settings import get_settings


@async_lru.alru_cache
async def get_temporal_client() -> client.Client:
    """
    Get Temporal Client
    """
    config = get_settings()
    await create_temporal_namespace()
    return await client.Client.connect(
        config.temporal.dsn,
        namespace=config.temporal.namespace,
        data_converter=DataConverter(payload_converter_class=PydanticPayloadConverter),
    )


async def create_temporal_namespace() -> None:
    """
    Create Temporal Namespace
    """
    config = get_settings()
    _client = await client.Client.connect(config.temporal.dsn)
    try:
        await _client.workflow_service.register_namespace(
            RegisterNamespaceRequest(
                namespace=config.temporal.namespace,
                workflow_execution_retention_period=Duration(seconds=30 * 24 * 60 * 60),  # 30 days
            ),
        )
        logger.info(f"Temporal Namespace {config.temporal.namespace} created successfully")
    except RPCError as rpc_err:
        if rpc_err.status == RPCStatusCode.ALREADY_EXISTS:
            logger.info(f"Temporal Namespace {config.temporal.namespace} already exists")
            return  # update namespace if needed
        raise
