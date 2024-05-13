import abc
import dataclasses


@dataclasses.dataclass
class IODataclass:
    pass


class K8sResourceBaseClass(abc.ABC):

    @abc.abstractmethod
    def payload(self):
        """
        k8s resource payload
        """

    @abc.abstractmethod
    def put(self):
        """
        k8s server side apply
        """

    @abc.abstractmethod
    def delete(self):
        """
        k8s delete resource
        """