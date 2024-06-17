import abc


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
    async def approve(schema: dict) -> None:
        """
        Approve a product
        """
        raise NotImplementedError

    @staticmethod
    async def decline(schema: dict) -> None:
        """
        Decline a product
        """
        raise NotImplementedError
