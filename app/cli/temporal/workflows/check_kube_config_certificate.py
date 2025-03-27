from collections.abc import Callable
from datetime import timedelta

from loguru import logger
from temporalio import workflow
from temporalio.client import ScheduleIntervalSpec, ScheduleSpec

from app.cli.activity_util import run_activity
from app.cli.temporal.activities.check_kube_config_certificate import KubeConfigCertExpiryActivity
from app.cli.temporal.core.base import ScheduleWorkflow


@workflow.defn
class KubeConfigCertExpiryWorkflow(ScheduleWorkflow):
    @staticmethod
    def get_schedule_spec() -> ScheduleSpec:
        """
        Returns the schedule spec for the workflow
        """
        return ScheduleSpec(
            intervals=[ScheduleIntervalSpec(every=timedelta(days=1))],
            jitter=timedelta(minutes=5),
        )

    @classmethod
    def get_workflow_id(cls: type["KubeConfigCertExpiryWorkflow"]) -> str:
        """
        Returns the workflow id based on the input
        """
        return cls.__name__

    @staticmethod
    def get_activities() -> list[type[Callable]]:
        """
        Returns the list of activities used in this workflow
        """
        return [KubeConfigCertExpiryActivity.defn]

    @workflow.run
    async def run(self: "ScheduleWorkflow") -> None:
        """
        Run the workflow
        """
        await run_activity(activity=KubeConfigCertExpiryActivity, arg=None)
        logger.info("CheckKubeConfigCertExpiry Workflow completed")
