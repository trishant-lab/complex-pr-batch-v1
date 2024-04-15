from kubernetes import client, config
from kubernetes.client.rest import ApiException
from loguru import logger


class PVC:
    """
    Class to handle PVC setup
    """

    def __init__(self, namespace: str, pvc_name: str, storage: str):
        self.namespace: str = namespace
        self.pvc_name: str = pvc_name
        self.storage: str = storage

    async def create(self):
        """
        Create a PVC in a namespace
        """
        config.load_kube_config()

        try:
            with client.ApiClient() as api_client:
                api_instance = client.CoreV1Api(api_client)

                # get the PVC
                response = api_instance.list_namespaced_persistent_volume_claim(
                    namespace=self.namespace,
                    field_selector=f"metadata.name={self.pvc_name}"
                )

                if response.items:
                    logger.info(f"PVC {self.pvc_name} already exists in namespace {self.namespace}")

                    return

                body = client.V1PersistentVolumeClaim(
                    api_version="v1",
                    kind="PersistentVolumeClaim",
                    metadata=client.V1ObjectMeta(name=self.pvc_name),
                    spec=client.V1PersistentVolumeClaimSpec(
                        volume_mode="Filesystem",
                        storage_class_name="topolvm-provisioner",
                        access_modes=["ReadWriteOnce"],
                        resources=client.V1ResourceRequirements(
                            requests={"storage": self.storage}
                        ),
                    ),
                )

                api_instance.create_namespaced_persistent_volume_claim(namespace=self.namespace, body=body)

                return

        except ApiException as e:
            logger.error(f"Exception when calling CoreV1Api->create_namespaced_persistent_volume_claim: {e}")
            raise e

    async def delete(self) -> None:
        """
        Delete a PVC in a namespace
        """

        config.load_kube_config()

        try:
            with client.ApiClient() as api_client:
                api_instance = client.CoreV1Api(api_client)

                # get the PVC
                response = api_instance.list_namespaced_persistent_volume_claim(
                    namespace=self.namespace,
                    field_selector=f"metadata.name={self.pvc_name}"
                )

                if response.items:
                    api_instance.delete_namespaced_persistent_volume_claim(
                        namespace=self.namespace,
                        name=self.pvc_name
                    )

                # PVC does not exist
                logger.info(f"PVC {self.pvc_name} does not exist in namespace {self.namespace}")

        except ApiException as e:
            logger.error(f"Exception when calling CoreV1Api->delete_namespaced_persistent_volume_claim: {e}")
            raise e
