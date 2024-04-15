from kubernetes import client, config
from kubernetes.client import ApiException
from loguru import logger


class KubernetesJob:

    def __init__(self, namespace: str, job_name: str):
        self.namespace = namespace
        self.job_name = job_name

    async def get_current_job(self):
        """
        Get kubernetes job
        :return:
        """
        config.load_kube_config()

        try:
            with client.ApiClient() as api_client:
                api_instance = client.BatchV1Api(api_client)

                response = api_instance.list_namespaced_job(
                    namespace=self.namespace,
                    field_selector=f"metadata.name={self.job_name}"
                )
                return response

        except ApiException as e:
            logger.error(f"Error while getting job: {e}")
            raise e

    async def create_or_replace_job(self, body: str):
        """
        Create or replace kubernetes job
        :return:
        """
        config.load_kube_config()

        try:
            with client.ApiClient() as api_client:
                api_instance = client.BatchV1Api(api_client)

                # Check if the job already exists
                response = self.get_current_job()
                if response.items():
                    logger.info(f"{self.job_name} Job already exists for {self.namespace}")
                    return

                # Create a new job
                body = client.V1Job(metadata=client.V1ObjectMeta(name=self.job_name), spec=body)

                api_instance.create_namespaced_job(namespace=self.namespace, body=body)
                logger.info(f"{self.job_name} Job created for {self.namespace}")

        except ApiException as e:
            logger.error(f"Error while deleting namespace: {e}")
            raise e

    async def delete_job(self):
        """
        Delete kubernetes job
        :return:
        """
        config.load_kube_config()

        try:
            with client.ApiClient() as api_client:
                api_instance = client.BatchV1Api(api_client)

                api_instance.delete_namespaced_job(
                    name=self.job_name,
                    namespace=self.namespace
                )
                logger.info(f"{self.job_name} Job deleted for {self.namespace}")

        except ApiException as e:
            logger.error(f"Error while deleting job: {e}")
            raise e

    async def get_job_execution_status(self) -> client.V1JobStatus:
        """
        Check kubernetes job execution status
        :return:
        """
        config.load_kube_config()

        try:
            with client.ApiClient() as api_client:
                api_instance = client.BatchV1Api(api_client)

                response: client.V1Job = api_instance.read_namespaced_job_status(
                    name=self.job_name,
                    namespace=self.namespace
                )
                return response.status

        except ApiException as e:
            logger.error(f"Error while getting job status: {e}")
            raise e
