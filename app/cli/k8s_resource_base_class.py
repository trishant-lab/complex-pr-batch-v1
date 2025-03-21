import abc
import dataclasses


@dataclasses.dataclass
class IODataclass:
    pass


class K8sResourceBaseClass(abc.ABC):
    @abc.abstractmethod
    def payload(self: "K8sResourceBaseClass") -> dict:
        """
        k8s resource payload
        """

    @abc.abstractmethod
    def put(self: "K8sResourceBaseClass") -> None:
        """
        k8s server side apply
        """

    @abc.abstractmethod
    def delete(self: "K8sResourceBaseClass") -> None:
        """
        k8s delete resource
        """
