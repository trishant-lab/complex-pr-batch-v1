from kubernetes import client, config
from kubernetes.client.rest import ApiException
from loguru import logger


class KubernetesSecretService:
    """
    Class to handle secret setup

    """

    def __init__(self, namespace: str, secret_name: str, data: dict):
        self.namespace: str = namespace
        self.secret_name: str = secret_name
        self.data: dict = data

    async def create_or_replace(self):
        """
        Create a secret in a namespace
        """
        config.load_kube_config()
        try:
            v1 = client.CoreV1Api()

            # get the secret
            response = v1.list_namespaced_secret(
                namespace=self.namespace,
                field_selector=f"metadata.name={self.secret_name}"
            )
            # update the secret
            if response.items:
                response.data = self.data
                v1.replace_namespaced_secret(namespace=self.namespace, name=self.secret_name, body=response)

                logger.info(f"Secret {self.secret_name} updated")
                return

            body = client.V1Secret(
                api_version="v1",
                kind="Secret",
                metadata=client.V1ObjectMeta(name=self.secret_name),
                type="kubernetes.io/dockerconfigjson",
                data=self.data,
            )
            v1.create_namespaced_secret(namespace=self.namespace, body=body)

            logger.info(f"Secret {self.secret_name} created")
            return
        except ApiException as e:
            raise e

    async def delete(self) -> None:
        """

        :return:
        :rtype:
        """
        config.load_kube_config()
        try:
            v1 = client.CoreV1Api()
            response = v1.list_namespaced_secret(
                namespace=self.namespace,
                field_selector=f"metadata.name={self.secret_name}"
            )
            if not response.items:
                logger.info(f"Secret {self.secret_name} does not exist in namespace {self.namespace}")
                return
            v1.delete_namespaced_secret(name=self.secret_name, namespace=self.namespace)
            logger.info(f"Secret {self.secret_name} deleted")
        except ApiException as e:
            raise e
