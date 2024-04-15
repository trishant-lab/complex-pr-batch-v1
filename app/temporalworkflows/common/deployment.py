from kubernetes import client, config
from kubernetes.client import ApiException
from kubernetes import utils

from loguru import logger


class DeploymentJob:
    """
    Class to handle DeploymentJob setup
    """

    def __init__(self, namespace: str, deployment_name: str, image_tag: str, replicas: int, product_name: str):
        self.namespace: str = namespace
        self.deployment_name: str = deployment_name
        self.image_tag: str = image_tag
        self.replicas: int = replicas
        self.product_name: str = product_name
        self.cli_name: str = f"{self.deployment_name}-cli"
        self.port: int = 8000

    async def create_or_replace(self, body) -> None:
        """
        Create a DeploymentJob in a namespace
        """
        try:
            config.load_kube_config()

            with client.ApiClient() as api_client:
                api_instance = client.AppsV1Api(api_client)

                # get current deployment
                current_deployment = api_instance.read_namespaced_deployment(
                    namespace=self.namespace,
                    name=self.deployment_name
                ).get()

                # deploy the main service
                if current_deployment:
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
                pods = core_v1_api.list_namespaced_pod(
                    namespace=self.namespace
                ).list_items()

                for pod in pods:
                    if pod.metadata.name.startswith(self.product_name) and not pod.metadata.name.contains("job"):
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

                api_instance.delete_namespaced_deployment(
                    namespace=self.namespace,
                    name=self.deployment_name
                )

        except ApiException as e:
            logger.error(f"Exception when calling AppsV1Api->delete_namespaced_deployment: {e}")
            raise


# if __name__ == "__main__":
#     from app.temporalworkflows.template_env import get_env
#
#     template_env = get_env("veritable")
#     template = template_env.get_template("server_deployment.yaml")
#
#     deployment_config: str = template.render(
#         product_name="veritable",
#         image_tag="latest",
#         replicas=1,
#         namespace="onboarding",
#         request={"memory": "128Mi", "cpu": "100m"},
#         limit={"memory": "512Mi", "cpu": "500m"},
#     )
#
#     with client.ApiClient() as api_client:
#         api_instance = client.AppsV1Api(api_client)
#
#         api_instance.create_namespaced_deployment(
#             namespace="onboarding",
#             body=deployment_config
#         )
