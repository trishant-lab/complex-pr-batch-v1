from kubernetes.client import V1Namespace, V1ObjectMeta

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.jeeves.jeeves import JeevesSpec


class Namespace(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self: "Namespace", jeeves: JeevesSpec) -> None:
        """
        Constructor
        """
        self.jeeves: JeevesSpec = jeeves
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.Namespace, api_version="v1"
        )

    def payload(self: "Namespace") -> dict:
        """
        k8s resource payload
        """
        body = V1Namespace(
            api_version="v1", kind=ResourceKindEnum.Namespace.value, metadata=V1ObjectMeta(name=f"{self.jeeves.tenant}")
        )

        return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

    def put(self: "Namespace") -> None:
        """
        k8s server side apply
        """
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource, body=self.payload(), field_manager="kubectl-client-side-apply"
        )

    def delete(self: "Namespace") -> None:
        """
        Don't delete namespace
        """
        # Don't delete namespace, it will delete all resources in the namespace.
        # Work with devops team to delete namespace if needed
        pass
