from kubernetes import config, client
from kubernetes.client import ApiException
from loguru import logger


class VMPodScrapper:
    """
    Class to handle VM Pod Scrapper
    """

    def __init__(self, namespace: str, name: str):
        self.namespace: str = namespace
        self.name: str = name
        self.group = "operator.victoriametrics.com"
        self.version = "v1beta1"
        self.plural = "vmpodscrapes"

    def create_or_replace(self, body: dict):
        """
        Create or replace a VM pod in a namespace
        """
        config.load_kube_config()
        try:
            v1 = client.CustomObjectsApi()

            response = v1.list_namespaced_custom_object(
                group=self.group,
                version=self.version,
                namespace=self.namespace,
                plural=self.plural,
                field_selector=f"metadata.name={self.name}"
            )

            body["apiVersion"] = f"{self.group}/{self.version}"

            if response.get('items'):
                logger.info(f"VM Pod Scrape {self.name} already exists in namespace {self.namespace}. Updating it")

                body["metadata"]["resourceVersion"] = response["items"][0]["metadata"]["resourceVersion"]

                v1.replace_namespaced_custom_object(
                    group=self.group,
                    version=self.version,
                    namespace=self.namespace,
                    plural=self.plural,
                    name=self.name,
                    body=body
                )
                return

            # Create new VM Pod Scrape if it doesn't exist
            v1.create_namespaced_custom_object(
                group=self.group,
                version=self.version,
                namespace=self.namespace,
                plural=self.plural,
                body=body
            )
            logger.info(f"VM Pod Scrape {self.name} created successfully for namespace {self.namespace}")
            return None

        except ApiException as e:
            raise e

    async def delete(self):
        """
        Delete a VM pod in a namespace
        """
        config.load_kube_config()
        try:
            v1 = client.CustomObjectsApi()

            response = v1.list_namespaced_custom_object(
                group=self.group,
                version=self.version,
                namespace=self.namespace,
                plural=self.plural,
                field_selector=f"metadata.name={self.name}"
            )

            if not response.get('items'):
                logger.info(f"VM Pod Scrape {self.name} does not exist in namespace {self.namespace}")
                return

            v1.delete_namespaced_custom_object(
                group=self.group,
                version=self.version,
                namespace=self.namespace,
                plural=self.plural,
                name=self.name
            )
            logger.info(f"VM Pod Scrape {self.name} deleted successfully from namespace {self.namespace}")
            return None

        except ApiException as e:
            raise e
