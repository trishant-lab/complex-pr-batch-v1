from kubernetes.client import V1ObjectMeta, V1Secret

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.dexit.dexit import DexitSpec


class Secret(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(
        self: "Secret",
        dexit: DexitSpec,
        name: str,
        type: None | str = None,
        data: None | dict = None,
        string_data: None | dict = None,
    ) -> None:
        """
        dexit: DexitSpec
        name: str
        type: str
        data: dict: base64 encoded data
        string_data: dict  plain text data
        Need to send base64 encoded data or plain text data
        """
        self.name = name
        self.type = type
        self.data = data
        self.string_data = string_data
        self.dexit: DexitSpec = dexit
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.Secret, api_version="v1"
        )

    def payload(self: "Secret") -> dict:
        """
        Payload
        """
        body: V1Secret = V1Secret(
            api_version="v1",
            kind=ResourceKindEnum.Secret.value,
            metadata=V1ObjectMeta(namespace=self.dexit.tenant, name=self.name),
            type=self.type,
            data=self.data,
            string_data=self.string_data,
        )

        return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

    def put(self: "Secret") -> None:
        """
        Put
        """
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource, body=self.payload(), field_manager="kubectl-client-side-apply"
        )

    def delete(self: "Secret") -> None:
        """
        Delete
        """
        # Don't delete secret.
        # Work with devops team to secret if needed
        pass
