import abc
import dataclasses
from collections.abc import Callable

from temporalio.common import RetryPolicy


@dataclasses.dataclass
class IODataclass:
    pass


class Activity(abc.ABC):

    @staticmethod
    @abc.abstractmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """

    @staticmethod
    @abc.abstractmethod
    async def defn(activity_input: IODataclass | None) -> IODataclass | None:
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
    def get_workflow_id(cls: "Workflow", workflow_input: IODataclass) -> str | None:
        """
        Return unique workflow id from workflow input, guarantees exactly one execution of workflow
        - Add combination of one or more fields from `workflow_input` to uniquely identify workflow
        """

    @abc.abstractmethod
    async def run(self: "Workflow", workflow_input: IODataclass | None) -> IODataclass | None:
        """
        Entry point for workflow
        """

    @staticmethod
    def approve(self: "Workflow") -> None:
        """
        Signal the workflow
        """
        pass
