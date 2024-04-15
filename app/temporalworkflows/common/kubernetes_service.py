from kubernetes import client, config
from loguru import logger


class KubernetesService:
    """
    Class to handle Kubernetes service setup
    """

    def __init__(self, namespace: str, product_name: str, port: int):
        self.namespace: str = namespace
        self.product_name: str = product_name
        self.port: int = port

    async def create_or_replace(self) -> dict:
        """
        Create or replace a service in a namespace
        """
        config.load_kube_config()
        v1 = client.CoreV1Api()

        body = client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=client.V1ObjectMeta(
                name=self.product_name,
                labels={"app": self.product_name},
                managed_fields=[client.V1ManagedFieldsEntry(manager="kubectl-client-side-apply")]
            ),
            spec=client.V1ServiceSpec(
                selector={"app": self.product_name},
                type="ClusterIP",
                ports=[
                    client.V1ServicePort(
                        name="http",
                        port=self.port,
                    )
                ]
            )
        )

        current_service = (
            v1.connect_get_namespaced_service_proxy(namespace=self.namespace, name=self.product_name).get()
        )

        # If the service already exists, update it
        if current_service:
            response = v1.replace_namespaced_service(namespace=self.namespace, name=self.product_name, body=body)
            return response.to_dict()

        # If the service does not exist, create it
        response = v1.create_namespaced_service(namespace=self.namespace, body=body)
        return response.to_dict()

    async def delete(self) -> None:
        """
        Delete a service in a namespace
        :return:
        """
        config.load_kube_config()
        v1 = client.CoreV1Api()

        current_service = v1.connect_get_namespaced_service_proxy(namespace=self.namespace, name=self.product_name).get()

        if current_service:
            logger.info("Deleting service")
            v1.delete_namespaced_service(namespace=self.namespace, name=self.product_name)
        else:
            logger.info("Service does not exist in namespace")
