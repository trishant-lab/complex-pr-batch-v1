from kubernetes import client, config
from kubernetes.client import ApiException

from loguru import logger


class DeploymentJob:
    """
    Class to handle DeploymentJob setup
    """

    def __init__(self, namespace: str, deployment_name: str, product_name: str):
        self.namespace: str = namespace
        self.deployment_name: str = deployment_name
        self.product_name: str = product_name

    async def create_or_replace(self, body: client.V1Deployment) -> None:
        """
        Create a DeploymentJob in a namespace
        """
        try:
            config.load_kube_config()

            with client.ApiClient() as api_client:
                api_instance = client.AppsV1Api(api_client)

                # get current deployment
                current_deployment = api_instance.list_namespaced_deployment(
                    namespace=self.namespace,
                    field_selector=f"metadata.name={self.deployment_name}"
                )

                # deploy the main service
                if current_deployment.items:
                    logger.info(f"Updating deployment: {self.deployment_name}")
                    api_instance.replace_namespaced_deployment(
                        namespace=self.namespace,
                        name=self.deployment_name,
                        body=body
                    )
                else:
                    api_instance.create_namespaced_deployment(
                        namespace=self.namespace,
                        body=body
                    )

                # get pods for the deployment
                core_v1_api = client.CoreV1Api(api_client)
                pods: client.V1PodList = core_v1_api.list_namespaced_pod(
                    namespace=self.namespace
                )

                for pod in pods.items:
                    if pod.metadata.name.startswith(self.product_name) and not pod.metadata.name.__contains__("job"):
                        # delete the pod
                        core_v1_api.delete_namespaced_pod(
                            namespace=self.namespace,
                            name=pod.metadata.name
                        )

        except ApiException as e:
            logger.error(f"Exception when calling AppsV1Api->create_namespaced_deployment: {e}")
            raise e

    async def delete(self) -> None:
        """
        Delete a DeploymentJob in a namespace
        """
        try:
            config.load_kube_config()

            with client.ApiClient() as api_client:
                api_instance = client.AppsV1Api(api_client)

                # get current deployment
                current_deployment = api_instance.list_namespaced_deployment(
                    namespace=self.namespace,
                    field_selector=f"metadata.name={self.deployment_name}"
                )

                if not current_deployment.items:
                    logger.info(f"Deployment: {self.deployment_name} does not exist in namespace: {self.namespace}")
                    return

                api_instance.delete_namespaced_deployment(
                    namespace=self.namespace,
                    name=self.deployment_name
                )

        except ApiException as e:
            logger.error(f"Exception when calling AppsV1Api->delete_namespaced_deployment: {e}")
            raise
