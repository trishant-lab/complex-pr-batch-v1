from kubernetes.client import V1ObjectMeta, V1PersistentVolumeClaim, V1PersistentVolumeClaimSpec, V1ResourceRequirements
from kubernetes.dynamic.exceptions import NotFoundError
from loguru import logger

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.temporal.core.log import log_info


class PVC(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self: "PVC", tenant: str, pvc_name: str, env: str) -> None:
        """
        Constructor
        """
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.PersistentVolumeClaim, api_version="v1"
        )
        self.pvc_name = pvc_name
        self.tenant = tenant
        self.env = env

    def payload(self: "PVC") -> dict:
        """
        k8s resource payload
        """
        body = V1PersistentVolumeClaim(
            api_version="v1",
            kind=ResourceKindEnum.PersistentVolumeClaim.value,
            metadata=V1ObjectMeta(namespace=self.tenant, name=self.pvc_name),
            spec=V1PersistentVolumeClaimSpec(
                volume_mode="Filesystem",
                storage_class_name="longhorn-replicated" if self.env == "integration" else "topolvm-provisioner",
                access_modes=["ReadWriteOnce"],
                resources=V1ResourceRequirements(requests={"storage": "1Gi"}),
            ),
        )

        return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

    def put(self: "PVC") -> None:
        """
        k8s server side apply
        """
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource, body=self.payload(), field_manager="kubectl-client-side-apply"
        )
        log_info(f"PVC {self.pvc_name} created successfully")

    def delete(self: "PVC") -> None:
        """
        k8s server side apply
        """
        try:
            self.k8s_dynamic_client.delete(resource=self.resource, name=self.pvc_name, namespace=self.tenant)
        except NotFoundError:
            logger.error(f"PVC {self.pvc_name} not found in namespace {self.tenant}")
