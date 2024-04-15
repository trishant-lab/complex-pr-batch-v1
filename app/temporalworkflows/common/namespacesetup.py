from kubernetes import config, client
from kubernetes.client import ApiException, V1NamespaceList
from loguru import logger


class Namespace:
    """
    Class to handle namespace setup

    """

    def __init__(self, namespace):
        self.namespace = namespace

    async def create(self) -> None:
        """
        :return:
        """
        config.load_kube_config()

        try:
            with client.ApiClient() as api_client:
                api_instance = client.CoreV1Api(api_client)

                # Check if the namespace already exists
                response: V1NamespaceList = api_instance.list_namespace(
                    field_selector=f"metadata.name={self.namespace}"
                )
                if response.items:
                    logger.info(f"Namespace {self.namespace} already exists")
                    return

                # Create a new namespace
                namespace = client.V1Namespace(metadata=client.V1ObjectMeta(name=self.namespace))
                api_instance.create_namespace(namespace)
                logger.info(f"Namespace {self.namespace} created")

        except ApiException as e:
            logger.error(f"Error while creating namespace: {e}")
            raise e

    async def delete(self) -> None:
        """
        :return:
        """
        config.load_kube_config()

        try:
            with client.ApiClient() as api_client:
                api_instance = client.CoreV1Api(api_client)

                # Check if the namespace already exists
                response: V1NamespaceList = api_instance.list_namespace(
                    field_selector=f"metadata.name={self.namespace}"
                )
                if not response.items:
                    logger.info(f"Namespace {self.namespace} does not exist")
                    return

                # Delete the namespace
                api_instance.delete_namespace(self.namespace)
                logger.info(f"Namespace {self.namespace} deleted")

        except ApiException as e:
            logger.error(f"Error while deleting namespace: {e}")
            raise e
