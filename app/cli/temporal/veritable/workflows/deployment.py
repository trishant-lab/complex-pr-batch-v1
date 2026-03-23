from collections.abc import Callable
from typing import TYPE_CHECKING

import pydash
from cryptography.fernet import Fernet
from temporalio import workflow

from app.cli.activity_util import run_activity
from app.cli.k8s_util import ResourceKindEnum
from app.cli.temporal.activities.cloudflare_setup import (
    CopyArtifactsToBucketActivity,
    CreateCloudflareBucketActivity,
    CreateCloudflareBucketCredentialsActivity,
    CreateCloudflareDNSRecordActivity,
    LinkBucketToDomainActivity,
    PropagateDNSRecordActivity,
)
from app.cli.temporal.activities.veritable_db_migration_job import (
    VeritableDatabaseMigrationJobActivity,
)
from app.cli.temporal.activities.deployment_pod_creation import (
    KubernetesDeploymentActivity,
    KubernetesDeploymentActivityModel,
)
from app.cli.temporal.activities.k8s_config_map import K8sConfigMapCreationActivity, K8sConfigMapCreationActivityModel
from app.cli.temporal.activities.k8s_istio_virtual_service import (
    KubernetesIstioVirtualServiceActivity,
    KubernetesIstioVirtualServiceActivityModel,
)
from app.cli.temporal.activities.k8s_namespace import K8sNamespaceCreationActivity, K8sNamespaceCreationActivityModel
from app.cli.temporal.activities.k8s_secret import (
    K8sSecretCreationActivity,
    K8sSecretCreationActivityModel,
    K8sSecretFetchActivity,
    K8sSecretFetchActivityModel,
)
from app.cli.temporal.activities.k8s_service import KubernetesServiceActivity, KubernetesServiceActivityModel
from app.cli.temporal.activities.keycloak_setup import (
    KeycloakRealmSetupActivity,
    KeycloakRealmSetupActivityModel,
)
from app.cli.temporal.activities.one_password import (
    OnePasswordGetActivity,
    OnePasswordGetActivityModel,
    OnePasswordInsertIfNotExistsActivity,
    OnePasswordInsertIfNotExistsActivityModel,
)
from app.cli.temporal.activities.postgres_setup import (
    PostgresDatabaseCreationActivity,
    PostgresDatabaseCreationActivityModel,
    PostgresGrantAccessToUserActivity,
    PostgresGrantAccessToUserActivityModel,
    PostgresSchemaCreationActivity,
    PostgresSchemaCreationActivityModel,
    PostgresSupavisorPollUserActivity,
    PostgresSupavisorPollUserActivityModel,
    PostgresUserCreationActivity,
    PostgresUserCreationActivityModel,
)
from app.cli.temporal.activities.redis import CACHE_HOST, RedisSetupActivity, RedisSetupActivityModel
from app.cli.temporal.activities.stateful_set_pod_creation import (
    CheckPodRunningStatusActivity,
    CheckPodRunningStatusActivityModel,
    StatefulSetPodDeletionActivity,
    StatefulSetPodDeletionActivityModel,
)
from app.cli.temporal.activities.temporal_namespace import (
    TemporalNamespaceActivity,
    TemporalNamespaceActivityModel,
)
from app.cli.temporal.activities.tenant_crd import (
    TenantCrdCreationActivity,
    TenantCrdCreationActivityModel,
)
from app.cli.temporal.activities.veritable_novu_setup import VeritableNovuOnboardingActivity
from app.cli.temporal.activities.vm_pod_scrapper import VMPodScrapperActivity, VMPodScrapperActivityModel
from app.cli.temporal.core.base import Workflow
from app.cli.temporal.models.cloudflare import (
    CopyArtifactsToBucketActivityModel,
    CreateCloudflareBucketActivityModel,
    CreateCloudflareBucketCredentialsActivityModel,
    CreateCloudflareDNSRecordActivityModel,
    LinkBucketToDomainActivityModel,
    PropagateDNSRecordActivityModel,
)
from app.cli.temporal.veritable import TemplatePath
from app.cli.temporal.veritable.models.veritable_spec import VeritableSpec
from app.common import generate_password
from app.core.ijson import ijson_dumps, ijson_loads
from app.core.settings import AppSettings, VeritableSettings, get_settings
from app.models.product import ProductEnum
from app.template_env import get_env

if TYPE_CHECKING:
    from app.cli.temporal.models.cloudflare import CloudflareBucketCredentials

ProductName = "veritable"


@workflow.defn(sandboxed=False)
class VeritableDeploymentWorkflow(Workflow):
    """
    Veritable Deployment Workflow
    """

    @staticmethod
    def get_activities() -> list[type[Callable]]:  # type: ignore
        """
        Return list of activities used in the workflow
        """
        return [
            K8sNamespaceCreationActivity.defn,
            PostgresDatabaseCreationActivity.defn,
            PostgresUserCreationActivity.defn,
            PostgresSupavisorPollUserActivity.defn,
            PostgresSchemaCreationActivity.defn,
            PostgresGrantAccessToUserActivity.defn,
            K8sSecretCreationActivity.defn,
            RedisSetupActivity.defn,
            K8sConfigMapCreationActivity.defn,
            CreateCloudflareDNSRecordActivity.defn,
            CreateCloudflareBucketActivity.defn,
            CreateCloudflareBucketCredentialsActivity.defn,
            LinkBucketToDomainActivity.defn,
            PropagateDNSRecordActivity.defn,
            CopyArtifactsToBucketActivity.defn,
            KeycloakRealmSetupActivity.defn,
            VeritableDatabaseMigrationJobActivity.defn,
            KubernetesServiceActivity.defn,
            KubernetesIstioVirtualServiceActivity.defn,
            TemporalNamespaceActivity.defn,
            VMPodScrapperActivity.defn,
            TenantCrdCreationActivity.defn,
            OnePasswordInsertIfNotExistsActivity.defn,
            CheckPodRunningStatusActivity.defn,
            VeritableNovuOnboardingActivity.defn,
            KubernetesDeploymentActivity.defn,
            StatefulSetPodDeletionActivity.defn,
            OnePasswordGetActivity.defn,
            K8sSecretFetchActivity.defn,
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", veritable: VeritableSpec) -> str | None:
        """
        Return unique workflow id from workflow input, guarantees exactly one execution of workflow
        - Add combination of one or more fields from `workflow_input` to uniquely identify workflow
        """
        return f"veritable_deployment_workflow_{pydash.get(veritable, 'tenant')}"

    @workflow.run
    async def run(self: "Workflow", veritable: VeritableSpec) -> None:
        """
        Entry point for workflow
        """
        veritable = VeritableSpec.model_validate(veritable)

        config: AppSettings = get_settings()
        veritable_config: VeritableSettings = config.veritable

        tenant = pydash.get(veritable, "tenant")

        try:
            postgres_schema_name = f"{ProductName}_{tenant}"
            postgres_database_name = ProductName
            postgres_username = f"{ProductName}_{tenant}"
            postgres_password = generate_password(length=20)
            postgres_secret_name = f"{ProductName}-postgres"
            redis_tenant_password = generate_password(length=20)
            redis_secret_name = f"{ProductName}-redis"
            novu_secret_name = f"{ProductName}-novu"

            # create namespace in k8s
            await run_activity(
                activity=K8sNamespaceCreationActivity,
                arg=K8sNamespaceCreationActivityModel(namespace=tenant),
            )

            # check if redis secret exists
            redis_secret_exists = await run_activity(
                activity=K8sSecretFetchActivity,
                arg=K8sSecretFetchActivityModel(namespace=tenant, name=redis_secret_name, decode_data=True),
            )
            if redis_secret_exists:
                redis_tenant_password = redis_secret_exists["password"]

            # secret setup for redis password
            await run_activity(
                activity=K8sSecretCreationActivity,
                arg=K8sSecretCreationActivityModel(
                    namespace=tenant,
                    name=redis_secret_name,
                    string_data={"password": redis_tenant_password},
                ),
            )

            # check if postgres secret exists
            postgres_secret_exists = await run_activity(
                activity=K8sSecretFetchActivity,
                arg=K8sSecretFetchActivityModel(namespace=tenant, name=postgres_secret_name, decode_data=True),
            )
            if postgres_secret_exists:
                postgres_password = postgres_secret_exists["password"]

            # secret setup for postgres password
            await run_activity(
                activity=K8sSecretCreationActivity,
                arg=K8sSecretCreationActivityModel(
                    namespace=tenant,
                    name=postgres_secret_name,
                    string_data={"password": postgres_password},
                ),
            )

            # create postgres database
            await run_activity(
                activity=PostgresDatabaseCreationActivity,
                arg=PostgresDatabaseCreationActivityModel(database_name=postgres_database_name),
            )

            # create postgres user for veritable
            await run_activity(
                activity=PostgresUserCreationActivity,
                arg=PostgresUserCreationActivityModel(
                    username=postgres_username,
                    database_name=postgres_database_name,
                    password=postgres_password,
                ),
            )

            await run_activity(
                activity=PostgresSupavisorPollUserActivity,
                arg=PostgresSupavisorPollUserActivityModel(
                    username=postgres_username,
                    database_name=postgres_database_name,
                    db_password=postgres_password,
                    template_path=TemplatePath,
                ),
            )

            await run_activity(
                activity=PostgresSchemaCreationActivity,
                arg=PostgresSchemaCreationActivityModel(
                    schema_name=postgres_schema_name,
                    username=postgres_username,
                    database_name=postgres_database_name,
                ),
            )

            await run_activity(
                activity=PostgresGrantAccessToUserActivity,
                arg=PostgresGrantAccessToUserActivityModel(
                    schema_name=postgres_schema_name,
                    username=postgres_username,
                    database_name=postgres_database_name,
                ),
            )

            novu_api_key = await run_activity(
                activity=VeritableNovuOnboardingActivity,
                arg=veritable,
            )

            await run_activity(
                activity=K8sSecretCreationActivity,
                arg=K8sSecretCreationActivityModel(
                    namespace=tenant,
                    name=novu_secret_name,
                    string_data={"api-key": novu_api_key},
                ),
            )

            # check if data bucket credentials exists in secret
            data_bucket_secret_name = "veritable-cloudflare-r2"
            data_bucket_secret_exists = await run_activity(
                activity=K8sSecretFetchActivity,
                arg=K8sSecretFetchActivityModel(namespace=tenant, name=data_bucket_secret_name, decode_data=True),
            )

            one_password_vault = ProductEnum.get_onepassword_vault_name(ProductEnum.veritable)

            if not data_bucket_secret_exists:
                data_bucket = veritable.cloudflare_r2_data_bucket

                await run_activity(
                    activity=CreateCloudflareBucketActivity,
                    arg=CreateCloudflareBucketActivityModel(bucket_name=data_bucket),
                )

                credentials: CloudflareBucketCredentials = await run_activity(
                    activity=CreateCloudflareBucketCredentialsActivity,
                    arg=CreateCloudflareBucketCredentialsActivityModel(
                        bucket_name=data_bucket,
                        read_only=False,
                    ),
                )

                cloudflare_r2_data_bucket_access_key: str
                cloudflare_r2_data_bucket_secret_key: str

                if credentials.exists:
                    cloudflare_r2_data_bucket_access_key = await run_activity(
                        activity=OnePasswordGetActivity,
                        arg=OnePasswordGetActivityModel(
                            tenant=tenant,
                            vault=one_password_vault,
                            server_item=f"veritable-tenant-config-{config.env.lower().strip()}",
                            secret_name="s3_access_key",
                        ),
                    )
                    cloudflare_r2_data_bucket_secret_key = await run_activity(
                        activity=OnePasswordGetActivity,
                        arg=OnePasswordGetActivityModel(
                            tenant=tenant,
                            vault=one_password_vault,
                            server_item=f"veritable-tenant-config-{config.env.lower().strip()}",
                            secret_name="s3_secret_key",
                        ),
                    )
                else:
                    cloudflare_r2_data_bucket_access_key = credentials.access_key
                    cloudflare_r2_data_bucket_secret_key = credentials.secret_key

                    # s3 access key added to onepassword
                    await run_activity(
                        activity=OnePasswordInsertIfNotExistsActivity,
                        arg=OnePasswordInsertIfNotExistsActivityModel(
                            tenant=tenant,
                            vault=one_password_vault,
                            server_item=f"veritable-tenant-config-{config.env.lower().strip()}",
                            key="s3_access_key",
                            key_value=cloudflare_r2_data_bucket_access_key,
                        ),
                    )

                    # s3 secret key added to onepassword
                    await run_activity(
                        activity=OnePasswordInsertIfNotExistsActivity,
                        arg=OnePasswordInsertIfNotExistsActivityModel(
                            tenant=tenant,
                            vault=one_password_vault,
                            server_item=f"veritable-tenant-config-{config.env.lower().strip()}",
                            key="s3_secret_key",
                            key_value=cloudflare_r2_data_bucket_secret_key,
                        ),
                    )

                await run_activity(
                    activity=K8sSecretCreationActivity,
                    arg=K8sSecretCreationActivityModel(
                        namespace=tenant,
                        name=data_bucket_secret_name,
                        string_data={
                            "access-key": cloudflare_r2_data_bucket_access_key,
                            "secret-key": cloudflare_r2_data_bucket_secret_key,
                        },
                    ),
                )

            # secret setup for docker registry
            await run_activity(
                activity=K8sSecretCreationActivity,
                arg=K8sSecretCreationActivityModel(
                    namespace=tenant,
                    name="registrycred",
                    type="kubernetes.io/dockerconfigjson",
                    data={
                        ".dockerconfigjson": config.docker_image_pull_secret,
                    },
                ),
            )

            # setup redis
            await run_activity(
                activity=RedisSetupActivity,
                arg=RedisSetupActivityModel(
                    namespace=tenant,
                    product=ProductName,
                    redis_tenant_password=redis_tenant_password,
                ),
            )

            # insert fernet key into 1Password if it doesn't exist
            fernet_key = Fernet.generate_key().decode()
            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=tenant,
                    vault=one_password_vault,
                    server_item=f"veritable-tenant-config-{config.env.lower().strip()}",
                    key="fernet_key",
                    key_value=fernet_key,
                ),
            )

            custom_config = "custom-config.json"
            env_config = "env-config.json"
            tenant_config = "tenant-config.json"
            provisioning_config = "provisioning-config.json"
            config_dir = "config"
            # kubernetes config map creation
            for config_map in [
                {
                    "name": "veritable-env-config",
                    "key": env_config,
                    "template_file_name": f"{config.env}-env-config.tmpl.json",
                },
                {
                    "name": "veritable-tenant-config",
                    "key": tenant_config,
                    "template_file_name": f"{config.env}-tenant-config.tmpl.json",
                },
                {
                    "name": "veritable-provisioning-config",
                    "key": provisioning_config,
                    "template_file_name": f"{config.env}-provisioning-config.tmpl.json",
                },
            ]:
                await run_activity(
                    activity=K8sConfigMapCreationActivity,
                    arg=K8sConfigMapCreationActivityModel(
                        namespace=tenant,
                        name=config_map["name"],
                        template_file_name=config_map.get("template_file_name", None),
                        data=config_map.get("data", None),
                        cloudflare_r2_folder_path="veritable-config",
                        template_payload={
                            "tenant": tenant,
                            "customerId": pydash.get(veritable, "customerId"),
                            "orgName": pydash.get(veritable, "organization"),
                        },
                        destination_file_name=config_map["key"],
                    ),
                )

            api_dns = f"{tenant}.api.{veritable_config.domain_name}"
            # dns setup
            await run_activity(
                activity=CreateCloudflareDNSRecordActivity,
                arg=CreateCloudflareDNSRecordActivityModel(
                    domain_name=api_dns,
                    zone_id=veritable_config.zone_id,
                    content=config.k8s_cname,
                ),
            )

            # create bucket
            ui_bucket = veritable.cloudflare_r2_ui_bucket
            await run_activity(
                activity=CreateCloudflareBucketActivity,
                arg=CreateCloudflareBucketActivityModel(bucket_name=ui_bucket),
            )

            ui_dns = f"{tenant}.{veritable_config.domain_name}"
            # link bucket to custom domain
            await run_activity(
                activity=LinkBucketToDomainActivity,
                arg=LinkBucketToDomainActivityModel(
                    bucket_name=ui_bucket,
                    domain_name=ui_dns,
                    zone_id=veritable_config.zone_id,
                ),
            )

            # propagate the dns record
            await run_activity(
                activity=PropagateDNSRecordActivity,
                arg=PropagateDNSRecordActivityModel(
                    domain_name=f"{tenant}.{veritable_config.domain_name}",
                ),
            )

            repo_name = "veritable-ui"
            image_tag = "production" if config.env == "production" else "sprint"

            src_object_name = f"{repo_name}/{image_tag}/bundle.zip"

            bundle_path = "bundle/dist"

            # copy artifacts to bucket
            await run_activity(
                activity=CopyArtifactsToBucketActivity,
                arg=CopyArtifactsToBucketActivityModel(
                    bucket_name=ui_bucket,
                    src_object_name=src_object_name,
                    dest_dir=f"{ui_bucket}/",
                    bundle_path=bundle_path,
                    bundle_name="bundle.zip",
                    tenant=tenant,
                ),
            )

            # keycloak realm setup
            realm_name = f"veritable_{tenant}"
            await run_activity(
                activity=KeycloakRealmSetupActivity,
                arg=KeycloakRealmSetupActivityModel(
                    tenant=tenant,
                    realm_name=realm_name,
                    domain=veritable_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_realm.json",
                    template_payload={
                        "customerClientRoles": ijson_dumps(["VT_CUSTOMER_ADMIN"]),
                        "domain_org": veritable_config.domain_name.split(".")[-1],
                        "jinja_env.autoescape": False,
                    },
                ),
            )

            image_tag = "veritable-latest" if config.env == "production" else "sprint"
            docker_image = f"registry.314ecorp.tech/veritable-app:{image_tag}"

            # kubernetes service
            await run_activity(
                activity=KubernetesServiceActivity,
                arg=KubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="veritable",
                    ports={"http": 8000},
                ),
            )

            template_env = get_env(template_path=TemplatePath)
            template = template_env.get_template("istio-rules.json")
            output = template.render(tenant=tenant, image_tag=image_tag)
            http_list = ijson_loads(output)
            # kubernetes virtual service
            await run_activity(
                activity=KubernetesIstioVirtualServiceActivity,
                arg=KubernetesIstioVirtualServiceActivityModel(
                    namespace=tenant,
                    host=api_dns,
                    service_name="veritable-vs",
                    payload=http_list,
                ),
            )

            # delete statefulset pod
            await run_activity(
                activity=StatefulSetPodDeletionActivity,
                arg=StatefulSetPodDeletionActivityModel(
                    namespace=tenant,
                    name="veritable",
                ),
            )

            # Deployment pod creation for server
            await run_activity(
                activity=KubernetesDeploymentActivity,
                arg=KubernetesDeploymentActivityModel(
                    namespace=tenant,
                    name="veritable",
                    docker_image=docker_image,
                    request_resource={
                        "cpu": pydash.get(veritable, "serverSpec.request_cpu"),
                        "memory": pydash.get(veritable, "serverSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(veritable, "serverSpec.limit_cpu"),
                        "memory": pydash.get(veritable, "serverSpec.limit_memory"),
                    },
                    container_ports={"http": 8000},
                    volume_mounts=[
                        {
                            "name": "custom-volume",
                            "mount_path": f"/{config_dir}/{custom_config}",
                            "sub_path": custom_config,
                        },
                        {
                            "name": "env-volume",
                            "mount_path": f"/{config_dir}/{env_config}",
                            "sub_path": env_config,
                        },
                        {
                            "name": "tenant-volume",
                            "mount_path": f"/{config_dir}/{tenant_config}",
                            "sub_path": tenant_config,
                        },
                        {
                            "name": "provisioning-volume",
                            "mount_path": f"/{config_dir}/{provisioning_config}",
                            "sub_path": provisioning_config,
                        },
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "veritable-tenant-config",
                            "key": tenant_config,
                            "path": tenant_config,
                        },
                        {
                            "name": "custom-volume",
                            "config_map_name": "veritable-custom-config",
                            "key": custom_config,
                            "path": custom_config,
                        },
                        {
                            "name": "env-volume",
                            "config_map_name": "veritable-env-config",
                            "key": env_config,
                            "path": env_config,
                        },
                        {
                            "name": "provisioning-volume",
                            "config_map_name": "veritable-provisioning-config",
                            "key": provisioning_config,
                            "path": provisioning_config,
                        },
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "APP_CONFIG_DIR", "value": "/config"},
                        {
                            "name": "POSTGRES__PASSWORD",
                            "value_from": {"secret_key_ref": {"name": postgres_secret_name, "key": "password"}},
                        },
                        {"name": "POSTGRES__USER", "value": postgres_username},
                        {"name": "REDIS__HOST", "value": CACHE_HOST},
                        {
                            "name": "REDIS__PASSWORD",
                            "value_from": {"secret_key_ref": {"name": redis_secret_name, "key": "password"}},
                        },
                        {"name": "RELEASE_VERSION", "value": image_tag},
                        {"name": "IS_CLI", "value": "FALSE"},
                        {"name": "ORG_NAME", "value": pydash.get(veritable, "organization")},
                        {"name": "PROVISIONING_CONFIG", "value": f"/{config_dir}/{provisioning_config}"},
                        {
                            "name": "NOVU__API_KEY",
                            "value_from": {"secret_key_ref": {"name": novu_secret_name, "key": "api-key"}},
                        },
                        {
                            "name": "TENANT_S3__ACCESS_KEY",
                            "value_from": {"secret_key_ref": {"name": "veritable-cloudflare-r2", "key": "access-key"}},
                        },
                        {
                            "name": "TENANT_S3__SECRET_KEY",
                            "value_from": {"secret_key_ref": {"name": "veritable-cloudflare-r2", "key": "secret-key"}},
                        },
                    ]
                    + (
                        [{"name": "SELECTED_APPS", "value": ijson_dumps(pydash.get(veritable, "selectedApps"))}]
                        if pydash.get(veritable, "selectedApps")
                        else []
                    ),
                ),
            )

            await run_activity(
                activity=StatefulSetPodDeletionActivity,
                arg=StatefulSetPodDeletionActivityModel(
                    namespace=tenant,
                    name="veritable-cli",
                ),
            )

            # Deployment pod creation for cli
            await run_activity(
                activity=KubernetesDeploymentActivity,
                arg=KubernetesDeploymentActivityModel(
                    namespace=tenant,
                    name="veritable-cli",
                    docker_image=docker_image,
                    request_resource={
                        "cpu": pydash.get(veritable, "cliSpec.request_cpu"),
                        "memory": pydash.get(veritable, "cliSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(veritable, "cliSpec.limit_cpu"),
                        "memory": pydash.get(veritable, "cliSpec.limit_memory"),
                    },
                    container_ports={"http": 8000},
                    volume_mounts=[
                        {
                            "name": "custom-volume",
                            "mount_path": f"/{config_dir}/{custom_config}",
                            "sub_path": custom_config,
                        },
                        {
                            "name": "env-volume",
                            "mount_path": f"/{config_dir}/{env_config}",
                            "sub_path": env_config,
                        },
                        {
                            "name": "tenant-volume",
                            "mount_path": f"/{config_dir}/{tenant_config}",
                            "sub_path": tenant_config,
                        },
                        {
                            "name": "provisioning-volume",
                            "mount_path": f"/{config_dir}/{provisioning_config}",
                            "sub_path": provisioning_config,
                        },
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "veritable-tenant-config",
                            "key": tenant_config,
                            "path": tenant_config,
                        },
                        {
                            "name": "custom-volume",
                            "config_map_name": "veritable-custom-config",
                            "key": custom_config,
                            "path": custom_config,
                        },
                        {
                            "name": "env-volume",
                            "config_map_name": "veritable-env-config",
                            "key": env_config,
                            "path": env_config,
                        },
                        {
                            "name": "provisioning-volume",
                            "config_map_name": "veritable-provisioning-config",
                            "key": provisioning_config,
                            "path": provisioning_config,
                        },
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "APP_CONFIG_DIR", "value": "/config"},
                        {
                            "name": "POSTGRES__PASSWORD",
                            "value_from": {"secret_key_ref": {"name": postgres_secret_name, "key": "password"}},
                        },
                        {"name": "POSTGRES__USER", "value": postgres_username},
                        {"name": "REDIS__HOST", "value": CACHE_HOST},
                        {
                            "name": "REDIS__PASSWORD",
                            "value_from": {"secret_key_ref": {"name": redis_secret_name, "key": "password"}},
                        },
                        {"name": "RELEASE_VERSION", "value": image_tag},
                        {"name": "IS_CLI", "value": "TRUE"},
                        {"name": "ORG_NAME", "value": pydash.get(veritable, "organization")},
                        {"name": "PROVISIONING_CONFIG", "value": f"/{config_dir}/{provisioning_config}"},
                        {
                            "name": "NOVU__API_KEY",
                            "value_from": {"secret_key_ref": {"name": novu_secret_name, "key": "api-key"}},
                        },
                        {
                            "name": "TENANT_S3__ACCESS_KEY",
                            "value_from": {"secret_key_ref": {"name": "veritable-cloudflare-r2", "key": "access-key"}},
                        },
                        {
                            "name": "TENANT_S3__SECRET_KEY",
                            "value_from": {"secret_key_ref": {"name": "veritable-cloudflare-r2", "key": "secret-key"}},
                        },
                    ]
                    + (
                        [{"name": "SELECTED_APPS", "value": ijson_dumps(pydash.get(veritable, "selectedApps"))}]
                        if pydash.get(veritable, "selectedApps")
                        else []
                    ),
                ),
            )

            # temporal namespace creation
            await run_activity(
                activity=TemporalNamespaceActivity,
                arg=TemporalNamespaceActivityModel(
                    namespace=f"veritable_{tenant}",
                ),
            )

            # vm pod scraper for server
            await run_activity(
                activity=VMPodScrapperActivity,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="veritable-metrics",
                    app="veritable",
                    path="/metrics/",
                    interval="5s",
                ),
            )

            # vm pod scraper
            await run_activity(
                activity=VMPodScrapperActivity,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="veritable-cli-metrics",
                    app="veritable-cli",
                    path="/metrics/",
                    interval="5s",
                ),
            )

            # check pod running status
            for pod in ["veritable", "veritable-cli"]:
                await run_activity(
                    activity=CheckPodRunningStatusActivity,
                    arg=CheckPodRunningStatusActivityModel(
                        namespace=tenant,
                        name=pod,
                    ),
                )

            # create tenant crd
            await run_activity(
                activity=TenantCrdCreationActivity,
                arg=TenantCrdCreationActivityModel(
                    tenant=tenant,
                    kind=ResourceKindEnum.VeritableTenant,
                    product=ProductName,
                    data=veritable.model_dump_json(),
                ),
            )

        except Exception as e:
            workflow.logger.error(f"Error in deployment workflow: {e}")
            raise e
