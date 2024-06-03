import abc


class ProductWorkflow(abc.ABC):

    @staticmethod
    @abc.abstractmethod
    async def onboard(schema: dict):
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    async def deboard(schema: dict):
        raise NotImplementedError
