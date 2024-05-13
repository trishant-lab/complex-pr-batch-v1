from kubernetes.client import V1Namespace, V1ObjectMeta, V1Secret

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.veritable.common import VeritableSpec
from app.core.settings import AppSettings, get_settings


class Secret(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self, veritable: VeritableSpec) -> None:
        self.veritable: VeritableSpec = veritable
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.Secret, api_version="v1"
        )
        self.config: AppSettings = get_settings()

    def payload(self):
        body = V1Secret(
            api_version="v1",
            kind=ResourceKindEnum.Secret.value,
            metadata=V1ObjectMeta(
                namespace=self.veritable.tenant,
                name="registrycred"
            ),
            type="kubernetes.io/dockerconfigjson",
            data={
                ".dockerconfigjson": self.config.docker_image_pull_secret
            }
        )

        return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

    def put(self):
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource,
            body=self.payload(),
            field_manager="kubectl-client-side-apply"
        )

    def delete(self):
        # Don't delete secret.
        # Work with devops team to secret if needed
        pass
