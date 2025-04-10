import abc

from temporalio.client import WorkflowHandle


class ProductWorkflow(abc.ABC):
    """
    Abstract class for product workflow
    """

    @staticmethod
    @abc.abstractmethod
    async def onboard(schema: dict) -> None:
        """
        Onboard a new product
        """
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    async def deboard(schema: dict) -> None:
        """
        Deboard a product
        """
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    async def deploy(schema: dict) -> None:
        """
        Deploy a product
        """
        raise NotImplementedError

    @staticmethod
    async def approve(schema: dict) -> None:
        """
        Approve a product
        """
        raise NotImplementedError

    @staticmethod
    async def approve_deprovisioning(schema: dict) -> None:
        """
        Approve deprovisioning a product
        """
        raise NotImplementedError

    @staticmethod
    async def deny_deprovisioning(schema: dict) -> None:
        """
        Deny deprovisioning a product
        """
        raise NotImplementedError

    @staticmethod
    async def decline(schema: dict) -> None:
        """
        Decline a product
        """
        raise NotImplementedError

    @staticmethod
    async def get_workflow_handle(schema: dict) -> WorkflowHandle:
        """
        Retry a product
        """
        raise NotImplementedError

    @staticmethod
    def get_workflow_id(schema: dict) -> str:
        """
        Get the workflow id for the given schema
        """
        raise NotImplementedError
