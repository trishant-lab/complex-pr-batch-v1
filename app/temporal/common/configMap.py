from kubernetes import client, config
from kubernetes.client import ApiException
from loguru import logger


class ConfigMap:
    """
    ConfigMap class for creating and updating ConfigMap
    """

    def __init__(self, namespace: str):
        self.namespace: str = namespace

    def create_or_replace_config(self, name: str, data: dict):
        """
        Apply the ConfigMap
        """
        config.load_kube_config()

        try:
            with client.ApiClient() as api_client:
                api_instance = client.CoreV1Api(api_client)

                # Check if the ConfigMap already exists
                response = api_instance.list_namespaced_config_map(
                    namespace=self.namespace,
                    field_selector=f"metadata.name={name}"
                )
                if response.items:
                    api_instance.replace_namespaced_config_map(
                        name=name,
                        namespace=self.namespace,
                        body=client.V1ConfigMap(
                            api_version="v1",
                            kind="ConfigMap",
                            metadata=client.V1ObjectMeta(name=name),
                            data=data
                        )
                    )
                    logger.info(f"ConfigMap {name} already exists. Updating it")
                    return

                # Create a new ConfigMap if it doesn't exist
                body = client.V1ConfigMap(
                    api_version="v1",
                    kind="ConfigMap",
                    metadata=client.V1ObjectMeta(name=name),
                    data=data
                )

                api_instance.create_namespaced_config_map(
                    namespace=self.namespace,
                    body=body
                )
        except ApiException as e:
            logger.error(f"Error while creating ConfigMap: {e}")
            raise e

        logger.info(f"ConfigMap {name} created successfully")

    async def delete_config(self, name: str):
        """
        Delete the ConfigMap
        """
        config.load_kube_config()

        try:
            with client.ApiClient() as api_client:
                api_instance = client.CoreV1Api(api_client)

                # Check if the ConfigMap exists
                response = api_instance.list_namespaced_config_map(
                    namespace=self.namespace,
                    field_selector=f"metadata.name={name}"
                )
                if not response.items:
                    logger.info(f"ConfigMap {name} does not exist in namespace: {self.namespace}")
                    return

                api_instance.delete_namespaced_config_map(
                    name=name,
                    namespace=self.namespace
                )
        except ApiException as e:
            logger.error(f"Error while deleting ConfigMap: {e}")
            raise e

        logger.info(f"ConfigMap {name} deleted successfully")
