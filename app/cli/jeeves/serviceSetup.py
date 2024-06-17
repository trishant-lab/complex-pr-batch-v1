from kubernetes.client import V1ObjectMeta, V1Service, V1ServicePort, V1ServiceSpec
from kubernetes.dynamic.exceptions import NotFoundError
from loguru import logger

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.jeeves.jeeves import JeevesSpec, ProductName


class Service(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self, jeeves: JeevesSpec) -> None:
        self.jeeves: JeevesSpec = jeeves
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.Service, api_version="v1"
        )

    def payload(self):
        body = V1Service(
            api_version="v1",
            kind=ResourceKindEnum.Service.value,
            metadata=V1ObjectMeta(
                name=ProductName,
                namespace=self.jeeves.tenant,
                labels={"app": ProductName},
            ),
            spec=V1ServiceSpec(
                selector={"app": ProductName},
                type="ClusterIP",
                ports=[
                    V1ServicePort(
                        name="http",
                        port=8000,
                    )
                ]
            )
        )

        return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

    def put(self):
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource,
            body=self.payload(),
            field_manager="kubectl-client-side-apply"
        )

    def delete(self):
        try:
            self.k8s_dynamic_client.delete(
                resource=self.resource,
                name=ProductName,
                namespace=self.jeeves.tenant
            )
        except NotFoundError as e:
            logger.error(f"Service {ProductName} not found in namespace {self.jeeves.tenant}")
