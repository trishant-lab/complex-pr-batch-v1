from temporalio import activity, workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from datetime import timedelta
    from tempfile import TemporaryDirectory

    import boto3

    from kubernetes.client import V1ConfigMap, V1ObjectMeta
    from app.cli.k8s_util import ResourceKindEnum, get_dynamic_client, get_resource
    from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
    from app.cli.temporal.core.log import log_info
    from app.core.settings import AppSettings, get_settings
    from app.onepasswordutil import secret_inject
    from app.s3_utils import download_file_from_storage, get_storage_client
    from app.template_env import get_env


class K8sConfigMapCreationActivityModel(LaunchpadCLIBaseModel):
    """
    K8sConfigMapCreationActivityModel
    """

    namespace: str
    name: str
    template_file_name: str
    bucket_name: str | None = None
    template_payload: dict


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
        env = app_config.env

        k8s_dynamic_client = get_dynamic_client()
        resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.ConfigMap, api_version="v1")

        template_file_name = f"""{env}-{activity_model.template_file_name
            .replace('.json', '.tmpl.json')
            .replace('.toml', '.tmpl.toml')
            .replace('.yaml', '.tmpl.yaml')
            .replace('.conf', '.tmpl.conf')
            .replace('.yml', '.tmpl.yml')
            }"""

        with TemporaryDirectory() as temp_dir:
            s3_int_client: boto3.client = get_storage_client(
                config=app_config,
                access_key=app_config.s3_int.access_key,
                secret_key=app_config.s3_int.secret_key,
                endpoint=app_config.s3_int.endpoint,
            )
            download_file_from_storage(
                object_name=template_file_name,
                file_path=f"{temp_dir}/{template_file_name}",
                storage_client=s3_int_client,
                bucket_name=activity_model.bucket_name,
            )

            template_env = get_env(template_path=temp_dir)

            template = template_env.get_template(template_file_name)
            output = template.render(**activity_model.template_payload)

            with open(f"{temp_dir}/{template_file_name}", "w") as f:
                f.write(output)

            # inject secret into tenant-config.json from 1Password
            secret_inject(
                source_file_path=f"{temp_dir}/{template_file_name}",
                destination_path=f"{temp_dir}/{activity_model.template_file_name}",
            )

            body = V1ConfigMap(
                api_version="v1",
                kind=ResourceKindEnum.ConfigMap.value,
                metadata=V1ObjectMeta(namespace=activity_model.namespace, name=activity_model.name),
                data={
                    activity_model.template_file_name: open(f"{temp_dir}/{activity_model.template_file_name}").read()
                },
            )

        payload = k8s_dynamic_client.client.sanitize_for_serialization(body)
        k8s_dynamic_client.server_side_apply(resource=resource, body=payload, field_manager="kubectl-client-side-apply")

        log_info(f"ConfigMap {activity_model.name} created successfully")
