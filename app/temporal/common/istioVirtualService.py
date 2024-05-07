from kubernetes import client, config
from kubernetes.client.rest import ApiException
from loguru import logger


class IstioVirtualService:
    """
    Class to handle Istio Virtual Service setup
    """

    def __init__(self, namespace: str, product: str):
        self.namespace: str = namespace
        self.product: str = product
        self.name = f"{self.product}-vs"
        self.istio_group = "networking.istio.io"
        self.istio_version = "v1beta1"

    async def create_or_replace(self, body: dict) -> None:
        """
        Create or replace a istio virtual service in a namespace
        """

        try:
            config.load_kube_config()
            custom_object_api = client.CustomObjectsApi()

            # get the virtual service
            current_virtual_service = custom_object_api.list_namespaced_custom_object(
                group=self.istio_group,
                version=self.istio_version,
                namespace=self.namespace,
                plural="virtualservices",
                field_selector=f"metadata.name={self.name}",
            )

            if current_virtual_service.get('items'):
                logger.info(f"Virtual Service {self.name} already exists in namespace {self.namespace} Updating it")

                body["metadata"]["resourceVersion"] = current_virtual_service["items"][0]["metadata"]["resourceVersion"]

                # update the virtual service
                custom_object_api.replace_namespaced_custom_object(
                    group=self.istio_group,
                    version=self.istio_version,
                    namespace=self.namespace,
                    plural="virtualservices",
                    name=self.name,
                    body=body,
                )
                return

            custom_object_api.create_namespaced_custom_object(
                group=self.istio_group,
                version=self.istio_version,
                namespace=self.namespace,
                plural="virtualservices",
                body=body,
            )

            logger.info(f"Virtual Service {self.name} created in namespace {self.namespace}")

        except ApiException as e:
            raise e

    async def delete(self):
        """
        Delete a virtual service in a namespace
        :return:
        :rtype:
        """

        try:
            config.load_kube_config()
            custom_object_api = client.CustomObjectsApi()

            # get the virtual service
            current_virtual_service = custom_object_api.list_namespaced_custom_object(
                group=self.istio_group,
                version=self.istio_version,
                namespace=self.namespace,
                plural="virtualservices",
                field_selector=f"metadata.name={self.name}",
            )

            if current_virtual_service.get('items'):
                logger.info("Deleting virtual service")
                custom_object_api.delete_namespaced_custom_object(
                    group=self.istio_group,
                    version=self.istio_version,
                    namespace=self.namespace,
                    plural="virtualservices",
                    name=self.name,
                )
                return

            logger.info("Virtual service does not exist in namespace")

            return
        except ApiException as e:
            raise e
