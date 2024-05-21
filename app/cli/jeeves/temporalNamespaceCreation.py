from google.protobuf.duration_pb2 import Duration
from loguru import logger
from temporalio import client
from temporalio.api.workflowservice.v1 import RegisterNamespaceRequest
from temporalio.service import RPCError, RPCStatusCode

from app.cli.jeeves.common import JeevesSpec
from app.core.settings import AppSettings, get_settings


class TemporalNamespaceCreation:
    def __init__(self, jeeves: JeevesSpec) -> None:
        self.jeeves: JeevesSpec = jeeves
        self.config: AppSettings = get_settings()
        self.namespace = f"jeeves_{self.jeeves.tenant}"

    async def create_temporal_namespace(self):
        """
        Create Temporal Namespace
        """
        _client = await client.Client.connect(self.config.temporal.dsn)
        try:
            await _client.workflow_service.register_namespace(
                RegisterNamespaceRequest(
                    namespace=self.namespace,
                    workflow_execution_retention_period=Duration(seconds=30 * 24 * 60 * 60),  # 30 days
                ),
            )
            logger.info(f"Temporal Namespace {self.namespace} created successfully")
        except RPCError as rpc_err:
            if rpc_err.status == RPCStatusCode.ALREADY_EXISTS:
                logger.info(f"Temporal Namespace {self.namespace} already exists")
                return  # update namespace if needed
            raise
