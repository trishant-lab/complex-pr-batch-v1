import abc
import dataclasses
from collections.abc import Callable
from datetime import timedelta

from pydantic import BaseModel, Extra
from temporalio.client import ScheduleSpec
from temporalio.common import RetryPolicy


@dataclasses.dataclass
class IODataclass:
    pass


class LaunchpadCLIBaseModel(BaseModel, extra=Extra.allow):
    pass


class Activity(abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def get_timeout() -> timedelta:
        """
        timeout for the activity
        """

    @staticmethod
    @abc.abstractmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """

    @staticmethod
    @abc.abstractmethod
    async def defn(activity_input: LaunchpadCLIBaseModel | None) -> LaunchpadCLIBaseModel | None:
        """
        Callable for the activity
        """


class Workflow(abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def get_activities() -> list[type[Callable]]:
        """
        Return list of activities used in the workflow
        """

    @classmethod
    @abc.abstractmethod
    def get_workflow_id(cls: "Workflow", workflow_input: LaunchpadCLIBaseModel) -> str | None:
        """
        Return unique workflow id from workflow input, guarantees exactly one execution of workflow
        - Add combination of one or more fields from `workflow_input` to uniquely identify workflow
        """

    @abc.abstractmethod
    async def run(self: "Workflow", workflow_input: LaunchpadCLIBaseModel | None) -> LaunchpadCLIBaseModel | None:
        """
        Entry point for workflow
        """

    @staticmethod
    def approve(self: "Workflow") -> None:
        """
        Signal the workflow
        """
        pass

    @staticmethod
    def decline(self: "Workflow") -> None:
        """
        Signal the workflow
        """
        pass


class ScheduleWorkflow(abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def get_schedule_spec() -> ScheduleSpec:
        """
        Return schedule spec for the workflow
        """

    @classmethod
    @abc.abstractmethod
    def get_workflow_id(cls: "ScheduleWorkflow") -> str | None:
        """
        Return unique workflow id from workflow input, guarantees exactly one execution of workflow
        - Add combination of one or more fields from `workflow_input` to uniquely identify workflow
        """

    @staticmethod
    def get_start_delay() -> timedelta | None:
        """
        set the start delay for the workflow
        """
        return None

    @abc.abstractmethod
    async def run(self: "ScheduleWorkflow") -> None:
        """
        Entry point for workflow
        """

    @staticmethod
    @abc.abstractmethod
    def get_activities() -> list[type[Callable]]:
        """
        Return list of activities used in the workflow
        """
