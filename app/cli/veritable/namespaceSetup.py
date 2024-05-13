from kubernetes.client import V1Namespace, V1ObjectMeta

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.veritable.common import VeritableSpec


class Namespace(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self, veritable: VeritableSpec) -> None:
        self.veritable: VeritableSpec = veritable
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.Namespace, api_version="v1"
        )

    def payload(self):

        body = V1Namespace(
            api_version="v1",
            kind=ResourceKindEnum.Namespace.value,
            metadata=V1ObjectMeta(name=f"{self.veritable.tenant}")
        )

        return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

    def put(self):
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource,
            body=self.payload(),
            field_manager="kubectl-client-side-apply"
        )

    def delete(self):
        # Don't delete namespace, it will delete all resources in the namespace.
        # Work with devops team to delete namespace if needed
        pass
