from kubernetes import client, config
from kubernetes.client.rest import ApiException
from loguru import logger


class IstioVirtualService:
    """
    Class to handle Istio Virtual Service setup
    """

    def __init__(self, namespace: str, product: str, domain_name: str, environment: str, image_tag: str):
        self.namespace: str = namespace
        self.product: str = product
        self.domain_name: str = domain_name
        self.environment: str = environment
        self.image_tag: str = image_tag
        self.name = f"{self.product}-vs"
        self.istio_group = "networking.istio.io"
        self.istio_version = "v1beta1"

    async def create_or_replace(self, body) -> None:
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
            ).get()

            if current_virtual_service:
                logger.info(f"Virtual Service {self.name} already exists in namespace {self.namespace} Updating it")

                # update the virtual service
                custom_object_api.replace_namespaced_custom_object(
                    group=self.istio_group,
                    version=self.istio_version,
                    namespace=self.namespace,
                    plural="virtualservices",
                    name=self.name,
                    body=body,
                )

            custom_object_api.create_namespaced_custom_object(
                group=self.istio_group,
                version=self.istio_version,
                namespace=self.namespace,
                plural="virtualservices",
                body=body,
            )

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

            name = f"{self.product}-vs"
            istio_group = "networking.istio.io"
            istio_version = "v1beta1"

            # get the virtual service
            current_virtual_service = custom_object_api.list_namespaced_custom_object(
                group=istio_group,
                version=istio_version,
                namespace=self.namespace,
                plural="virtualservices",
                field_selector=f"metadata.name={name}",
            ).get()

            if current_virtual_service:
                logger.info("Deleting virtual service")
                custom_object_api.delete_namespaced_custom_object(
                    group=istio_group,
                    version=istio_version,
                    namespace=self.namespace,
                    plural="virtualservices",
                    name=name,
                )
                return

            logger.info("Virtual service does not exist in namespace")

            return
        except ApiException as e:
            raise e
