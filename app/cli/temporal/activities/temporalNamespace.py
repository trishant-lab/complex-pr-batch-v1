from temporalio.common import RetryPolicy
from temporalio import activity, client, workflow


with workflow.unsafe.imports_passed_through():
    from datetime import timedelta
    from google.protobuf.duration_pb2 import Duration
    from temporalio.api.operatorservice.v1 import DeleteNamespaceRequest
    from temporalio.api.workflowservice.v1 import RegisterNamespaceRequest
    from temporalio.service import RPCError, RPCStatusCode

    from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
    from app.cli.temporal.core.log import log_info
    from app.core.settings import AppSettings, get_settings


class TemporalNamespaceActivityModel(LaunchpadCLIBaseModel):
    """
    TemporalNamespace dataclass
    """

    namespace: str


class TemporalNamespaceActivity(Activity):
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
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="TemporalNamespaceActivity")
    async def defn(activity_input: TemporalNamespaceActivityModel) -> None:
        """
        Callable for the activity
        """
        # Create temporal namespace

        config: AppSettings = get_settings()

        _client = await client.Client.connect(config.temporal.dsn)

        try:
            await _client.workflow_service.register_namespace(
                RegisterNamespaceRequest(
                    namespace=activity_input.namespace,
                    workflow_execution_retention_period=Duration(seconds=30 * 24 * 60 * 60),  # 30 days
                ),
            )
        except RPCError as rpc_err:
            if rpc_err.status == RPCStatusCode.ALREADY_EXISTS:
                log_info(f"Temporal Namespace {activity_input.namespace} already exists")
                return  # update namespace if needed
            raise


class DeleteTemporalNamespaceActivityModel(LaunchpadCLIBaseModel):
    """
    DeleteTemporalNamespaceActivityModel
    """

    namespace: str


class DeleteTemporalNamespaceActivity(Activity):
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
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="DeleteTemporalNamespaceActivity")
    async def defn(activity_input: DeleteTemporalNamespaceActivityModel) -> None:
        """
        Callable for the activity to delete a Temporal namespace
        """
        config: AppSettings = get_settings()
        _client = await client.Client.connect(config.temporal.dsn)

        try:
            await _client.service_client.operator_service.delete_namespace(
                DeleteNamespaceRequest(namespace=activity_input.namespace)
            )
            log_info(f"Temporal Namespace {activity_input.namespace} deleted successfully")
        except RPCError as rpc_err:
            if rpc_err.status == RPCStatusCode.NOT_FOUND:
                log_info(f"Temporal Namespace {activity_input.namespace} does not exist")
                return
            raise
