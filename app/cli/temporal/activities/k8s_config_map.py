import os
from datetime import timedelta

from kubernetes.client import V1ConfigMap, V1ObjectMeta
from kubernetes.dynamic.exceptions import NotFoundError
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.k8s_util import ResourceKindEnum, get_dynamic_client, get_resource
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_error, log_info
from app.core.settings import AppSettings, get_settings
from app.one_password_util import secret_inject, secret_inject_drop_empty
from app.s3_utils import download_file_from_storage
from app.template_env import get_env
from app.utils.file_operations import get_opendal_file_client
from app.utils.s3_operations import get_s3_client


class K8sConfigMapCreationActivityModel(LaunchpadCLIBaseModel):
    """
    K8sConfigMapCreationActivityModel
    read from minio
    """

    namespace: str
    name: str
    template_file_name: str | None = None
    data: str | None = None
    destination_file_name: str
    bucket_name: str | None = None
    cloudflare_r2_folder_path: str | None = None
    template_payload: dict
    drop_empty_secrets: bool = False


class K8sConfigMapCreationActivity(Activity):
    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        retry policy for the activity
        """
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=1, backoff_coefficient=2)

    @staticmethod
    @activity.defn(name="K8sConfigMapCreationActivity")
    async def defn(activity_model: K8sConfigMapCreationActivityModel) -> None:
        """
        Callable for the activity
        """
        app_config: AppSettings = get_settings()

        k8s_dynamic_client = get_dynamic_client()
        resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.ConfigMap, api_version="v1")

        template_file_name = activity_model.template_file_name

        bucket_name = (
            activity_model.bucket_name
            if activity_model.cloudflare_r2_folder_path is None
            else "launchpad-config-templates"
        )

        if activity_model.data:
            data = {
                activity_model.destination_file_name: activity_model.data,
            }
        else:
            opendal_file_operations = get_opendal_file_client()
            async with opendal_file_operations.temp_dir() as temp_dir:
                s3_client = (
                    get_s3_client(
                        access_key=app_config.s3_int.access_key,
                        secret_key=app_config.s3_int.secret_key,
                        endpoint=app_config.s3_int.endpoint,
                        bucket_name=bucket_name,
                    )
                    if activity_model.cloudflare_r2_folder_path is None
                    else get_s3_client(
                        access_key=app_config.cloudflare.r2_access_key,
                        secret_key=app_config.cloudflare.r2_secret_key,
                        endpoint=app_config.cloudflare.r2_endpoint,
                        bucket_name=bucket_name,
                    )
                )

                object_name = (
                    f"{activity_model.cloudflare_r2_folder_path}/{template_file_name}"
                    if activity_model.cloudflare_r2_folder_path is not None
                    else template_file_name
                )

                temp_dir_path = os.path.join(opendal_file_operations.tempdir_root, temp_dir)
                await download_file_from_storage(
                    object_name=object_name,
                    file_path=os.path.join(temp_dir_path, template_file_name),
                    storage_client=s3_client,
                )

                template_env = get_env(template_path=temp_dir_path)

                template = template_env.get_template(template_file_name)
                output = template.render(**activity_model.template_payload)

                opendal_file_operations = get_opendal_file_client()
                await opendal_file_operations.write_file(os.path.join(temp_dir_path, template_file_name), output)

                # inject secret into tenant-config.json from 1Password
                inject = secret_inject_drop_empty if activity_model.drop_empty_secrets else secret_inject
                await inject(
                    source_file_path=os.path.join(temp_dir_path, template_file_name),
                    destination_path=os.path.join(temp_dir_path, activity_model.destination_file_name),
                )

                data = {
                    activity_model.destination_file_name: await opendal_file_operations.read_file_str(
                        os.path.join(temp_dir_path, activity_model.destination_file_name)
                    )
                }

        body = V1ConfigMap(
            api_version="v1",
            kind=ResourceKindEnum.ConfigMap.value,
            metadata=V1ObjectMeta(namespace=activity_model.namespace, name=activity_model.name),
            data=data,
        )

        payload = k8s_dynamic_client.client.sanitize_for_serialization(body)
        k8s_dynamic_client.server_side_apply(
            resource=resource, body=payload, field_manager="kubectl-client-side-apply", force_conflicts=True
        )

        log_info(f"ConfigMap {activity_model.name} created successfully")


class K8sConfigMapCreatFromTemplateActivityModel(LaunchpadCLIBaseModel):
    """
    K8sConfigMapCreatFromTemplateActivityModel
    """

    namespace: str
    name: str
    template_file_name: str | None = None
    template_path: str | None = None
    data: str | None = None
    destination_file_name: str
    template_payload: dict


class K8sConfigMapCreatFromTemplateActivity(Activity):
    """
    K8sConfigMapCreatFromTemplateActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="K8sConfigMapCreatFromTemplateActivity")
    async def defn(activity_model: K8sConfigMapCreatFromTemplateActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_dynamic_client = get_dynamic_client()
        resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.ConfigMap, api_version="v1")

        template_file_name = activity_model.template_file_name

        if activity_model.data:
            data = {
                activity_model.destination_file_name: activity_model.data,
            }
        else:
            opendal_file_operations = get_opendal_file_client()
            async with opendal_file_operations.temp_dir() as temp_dir:
                template_env = get_env(template_path=activity_model.template_path)

                template = template_env.get_template(template_file_name)
                output = template.render(**activity_model.template_payload)

                opendal_file_operations = get_opendal_file_client()
                temp_dir_path = os.path.join(opendal_file_operations.tempdir_root, temp_dir)
                await opendal_file_operations.write_file(os.path.join(temp_dir_path, template_file_name), output)

                # inject secret into tenant-config.json from 1Password
                await secret_inject(
                    source_file_path=os.path.join(temp_dir_path, template_file_name),
                    destination_path=os.path.join(temp_dir_path, activity_model.destination_file_name),
                )

                data = {
                    activity_model.destination_file_name: await opendal_file_operations.read_file_str(
                        os.path.join(temp_dir_path, activity_model.destination_file_name)
                    )
                }

        body = V1ConfigMap(
            api_version="v1",
            kind=ResourceKindEnum.ConfigMap.value,
            metadata=V1ObjectMeta(namespace=activity_model.namespace, name=activity_model.name),
            data=data,
        )

        payload = k8s_dynamic_client.client.sanitize_for_serialization(body)
        k8s_dynamic_client.server_side_apply(
            resource=resource, body=payload, field_manager="kubectl-client-side-apply", force_conflicts=True
        )

        log_info(f"ConfigMap {activity_model.name} created successfully")


class DeleteK8sConfigMapActivityModel(LaunchpadCLIBaseModel):
    """
    DeleteK8sConfigMapActivityModel
    """

    namespace: str
    name: str


class DeleteK8sConfigMapActivity(Activity):
    """
    DeleteK8sConfigMapActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5, backoff_coefficient=2)

    @staticmethod
    @activity.defn(name="DeleteK8sConfigMapActivity")
    async def defn(activity_model: DeleteK8sConfigMapActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_dynamic_client = get_dynamic_client()
        resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.ConfigMap, api_version="v1")

        try:
            k8s_dynamic_client.delete(resource=resource, name=activity_model.name, namespace=activity_model.namespace)
        except NotFoundError:
            log_error(f"ConfigMap {activity_model.name} not found in namespace {activity_model.namespace}")

        log_info(f"ConfigMap {activity_model.name} deleted in namespace {activity_model.namespace}")
