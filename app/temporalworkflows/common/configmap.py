from kubernetes import client, config
from kubernetes.client import ApiException
from loguru import logger


class ConfigMap:
    """
    ConfigMap class for creating and updating ConfigMap
    """

    def __init__(self, tenant: str):
        self.tenant: str = tenant

    def apply_config(self, name: str, data: dict):
        """
        Apply the ConfigMap
        """
        config.load_kube_config()

        try:
            with client.ApiClient() as api_client:
                api_instance = client.CoreV1Api(api_client)
                body = client.V1ConfigMap(
                    api_version="v1",
                    kind="ConfigMap",
                    metadata=client.V1ObjectMeta(name=name),
                    data=data
                )

                api_instance.create_namespaced_config_map(
                    namespace=self.tenant,
                    body=body
                )
        except ApiException as e:
            logger.error(f"Error while creating ConfigMap: {e}")
            raise e

        logger.info(f"ConfigMap {name} created successfully")

    def delete_config(self, name: str):
        """
        Delete the ConfigMap
        """
        config.load_kube_config()

        try:
            with client.ApiClient() as api_client:
                api_instance = client.CoreV1Api(api_client)
                api_instance.delete_namespaced_config_map(
                    name=name,
                    namespace=self.tenant
                )
        except ApiException as e:
            logger.error(f"Error while deleting ConfigMap: {e}")
            raise e

        logger.info(f"ConfigMap {name} deleted successfully")
