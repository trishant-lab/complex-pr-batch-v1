from collections.abc import Callable

import pydash
from cryptography.fernet import Fernet
from temporalio import workflow

from app.cli.activity_util import run_activity
from app.cli.k8s_util import ResourceKindEnum
from app.cli.temporal.activities.cloudflare_setup import (
    CopyArtifactsToBucketActivity,
    CopyWebCoreToBucketActivity,
    CreateCloudflareBucketActivity,
    CreateCloudflareDNSRecordActivity,
    LinkBucketToDomainActivity,
    PropagateDNSRecordActivity,
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
from app.cli.temporal.activities.k8s_secret import K8sSecretCreationActivity, K8sSecretCreationActivityModel
from app.cli.temporal.activities.k8s_service import KubernetesServiceActivity, KubernetesServiceActivityModel
from app.cli.temporal.activities.keycloak_setup import (
    KeycloakCreateInternalUsersActivity,
    KeycloakCreateInternalUsersActivityModel,
    KeycloakCreateTenantCustomerAdminUserActivity,
    KeycloakCreateTenantCustomerAdminUserActivityModel,
    KeycloakRealmSetupActivity,
    KeycloakRealmSetupActivityModel,
)
from app.cli.temporal.activities.one_password import (
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
    PostgresUserCreationFromSecretActivity,
    PostgresUserCreationFromSecretActivityModel,
)
from app.cli.temporal.activities.practifly_job import (
    PractiflyJobActivity,
    PractiflyJobActivityModel,
)
from app.cli.temporal.activities.pvc_setup import PVCSetupActivity, PVCSetupActivityModel
from app.cli.temporal.activities.redis import RedisSetupFromSecretActivity, RedisSetupFromSecretActivityModel
from app.cli.temporal.activities.send_mail import (
    SendAfterProvisioningMailActivity,
    SendAfterProvisioningMailActivityModel,
    SendBeforeProvisioningMailActivity,
    SendBeforeProvisioningMailActivityModel,
)
from app.cli.temporal.activities.stateful_set_pod_creation import (
    CheckPodRunningStatusActivity,
    CheckPodRunningStatusActivityModel,
    StatefulSetPodDeletionActivity,
    StatefulSetPodDeletionActivityModel,
)
from app.cli.temporal.activities.temporal_namespace import TemporalNamespaceActivity, TemporalNamespaceActivityModel
from app.cli.temporal.activities.tenant_crd import (
    TenantCrdCreationActivity,
    TenantCrdCreationActivityModel,
    TenantCrdExistsActivity,
    TenantCrdExistsActivityModel,
)
from app.cli.temporal.activities.update_tenant_status import TenantCliStatus, UpdateTenantStatusActivity
from app.cli.temporal.activities.vm_pod_scrapper import VMPodScrapperActivity, VMPodScrapperActivityModel
from app.cli.temporal.core.base import Workflow
from app.cli.temporal.models.cloudflare import (
    CopyArtifactsToBucketActivityModel,
    CopyWebCoreToBucketActivityModel,
    CreateCloudflareBucketActivityModel,
    CreateCloudflareDNSRecordActivityModel,
    LinkBucketToDomainActivityModel,
    PropagateDNSRecordActivityModel,
)
from app.cli.temporal.practifly import TemplatePath
from app.cli.temporal.practifly.models.practifly_spec import PractiflyJobEnum, PractiflySpec
from app.common import generate_password
from app.core.ijson import ijson_dumps, ijson_loads
from app.core.settings import AppSettings, PractiflySettings, get_settings
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum
from app.template_env import get_env

ProductName = "practifly"


@workflow.defn(sandboxed=False)
class PractiflyOnboardingWorkflow(Workflow):
    """
    Practifly Onboarding Workflow
    """

    def __init__(self: "Workflow") -> None:
        self.approved: bool = False
        self.denied: bool = False

    @staticmethod
    def get_activities() -> list[type[Callable]]:  # type: ignore
        """
        Return list of activities used in the workflow
        """
        return [
            SendBeforeProvisioningMailActivity.defn,
            K8sNamespaceCreationActivity.defn,
            PostgresDatabaseCreationActivity.defn,
            PostgresUserCreationFromSecretActivity.defn,
            PostgresSupavisorPollUserActivity.defn,
            PostgresSchemaCreationActivity.defn,
            PostgresGrantAccessToUserActivity.defn,
            K8sSecretCreationActivity.defn,
            RedisSetupFromSecretActivity.defn,
            PVCSetupActivity.defn,
            KubernetesServiceActivity.defn,
            KubernetesIstioVirtualServiceActivity.defn,
            K8sConfigMapCreationActivity.defn,
            CreateCloudflareDNSRecordActivity.defn,
            CreateCloudflareBucketActivity.defn,
            LinkBucketToDomainActivity.defn,
            PropagateDNSRecordActivity.defn,
            KeycloakRealmSetupActivity.defn,
            KeycloakCreateTenantCustomerAdminUserActivity.defn,
            TemporalNamespaceActivity.defn,
            VMPodScrapperActivity.defn,
            PractiflyJobActivity.defn,
            CopyArtifactsToBucketActivity.defn,
            CopyWebCoreToBucketActivity.defn,
            StatefulSetPodDeletionActivity.defn,
            UpdateTenantStatusActivity.defn,
            SendAfterProvisioningMailActivity.defn,
            TenantCrdExistsActivity.defn,
            TenantCrdCreationActivity.defn,
            KeycloakCreateInternalUsersActivity.defn,
            CheckPodRunningStatusActivity.defn,
            OnePasswordInsertIfNotExistsActivity.defn,
            KubernetesDeploymentActivity.defn,
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", practifly: PractiflySpec) -> str:
        """
        Return workflow id
        """
        return f"practifly_onboarding_workflow_{pydash.get(practifly, 'tenant')}"

    @workflow.run
    async def run(self: "Workflow", practifly: PractiflySpec) -> None:
        """
        Run the workflow
        """
        config: AppSettings = get_settings()
        practifly_config: PractiflySettings = config.practifly

        tenant = pydash.get(practifly, "tenant")
        first_name = pydash.get(practifly, "firstName")
        last_name = pydash.get(practifly, "lastName")
        email = pydash.get(practifly, "email")
        organization = pydash.get(practifly, "organization")

        try:
            # get tenant crd
            tenant_crd_exists: bool = await run_activity(
                activity=TenantCrdExistsActivity,
                arg=TenantCrdExistsActivityModel(
                    tenant=tenant,
                    kind=ResourceKindEnum.PractiflyTenant,
                    product=ProductName,
                ),
            )

            if tenant_crd_exists:
                raise ValueError(f"Tenant {tenant} already exists")  # noqa: TRY301

            if not pydash.get(practifly, "emailSent"):
                await run_activity(
                    activity=SendBeforeProvisioningMailActivity,
                    arg=SendBeforeProvisioningMailActivityModel(
                        user_details={
                            "firstName": first_name,
                            "lastName": last_name,
                            "email": email,
                        },
                        product=ProductName,
                        from_name=practifly_config.sender_name,
                        email_from=practifly_config.sender_email,
                    ),
                )

            # Wait for approval or denial
            await workflow.wait_condition(lambda: self.approved or self.denied)

            # Update tenant status if request is declined
            if self.denied:
                await run_activity(
                    activity=UpdateTenantStatusActivity,
                    arg=TenantCliStatus(
                        tenant_name=tenant,
                        status=TenantStatusEnum.ApprovalDeclined,
                        error_msg="Request Declined",
                        product=ProductEnum.practifly,
                    ),
                )

            postgres_schema_name = tenant
            postgres_database_name = f"{ProductName}-{config.env}"
            postgres_username = f"{ProductName}_{tenant}"
            postgres_password = generate_password(length=20)
            postgres_secret_name = f"{ProductName}-postgres"

            redis_tenant_password = generate_password(length=20)
            redis_secret_name = f"{ProductName}-redis"

            template_env = get_env(template_path=TemplatePath)
            image_tag = "production" if config.env == "production" else "sprint"
            docker_image = f"registry.314ecorp.tech/practifly-server:{image_tag}"
            template = template_env.get_template("istio-rules.json")
            output = template.render(tenant=tenant, image_tag=image_tag)

            http_list = ijson_loads(output)
            if config.env != "production":
                http_list.append(
                    {
                        "name": "redirect",
                        "match": [{"uri": {"exact": "/"}}],
                        "redirect": {"uri": f"/{image_tag}/"},
                    }
                )

            # kubernetes namespace creation
            await run_activity(
                activity=K8sNamespaceCreationActivity,
                arg=K8sNamespaceCreationActivityModel(
                    namespace=tenant,
                ),
            )

            # secret setup for redis password
            await run_activity(
                activity=K8sSecretCreationActivity,
                arg=K8sSecretCreationActivityModel(
                    namespace=tenant,
                    name=redis_secret_name,
                    string_data={"password": redis_tenant_password},
                ),
            )

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
                arg=PostgresDatabaseCreationActivityModel(
                    database_name=postgres_database_name,
                ),
            )

            # create postgres user for practifly
            await run_activity(
                activity=PostgresUserCreationFromSecretActivity,
                arg=PostgresUserCreationFromSecretActivityModel(
                    username=postgres_username,
                    database_name=postgres_database_name,
                    secret_name=postgres_secret_name,
                    namespace=tenant,
                ),
            )

            # create postgres user in supavisor for practifly
            await run_activity(
                activity=PostgresSupavisorPollUserActivity,
                arg=PostgresSupavisorPollUserActivityModel(
                    username=postgres_username,
                    database_name=postgres_database_name,
                    db_password=postgres_password,
                    template_path=TemplatePath,
                ),
            )

            # create postgres schema
            await run_activity(
                activity=PostgresSchemaCreationActivity,
                arg=PostgresSchemaCreationActivityModel(
                    schema_name=postgres_schema_name,
                    username=postgres_username,
                    database_name=postgres_database_name,
                ),
            )

            # grant access to postgres user
            await run_activity(
                activity=PostgresGrantAccessToUserActivity,
                arg=PostgresGrantAccessToUserActivityModel(
                    schema_name=postgres_schema_name,
                    username=postgres_username,
                    database_name=postgres_database_name,
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

            # secret setup for redis master password
            await run_activity(
                activity=K8sSecretCreationActivity,
                arg=K8sSecretCreationActivityModel(
                    namespace=tenant,
                    name="cache-secret",
                    string_data={"REDIS_PASSWORD": config.cache_admin_password},
                ),
            )

            # setup redis
            await run_activity(
                activity=RedisSetupFromSecretActivity,
                arg=RedisSetupFromSecretActivityModel(
                    namespace=tenant,
                    product=ProductName,
                    secret_name=redis_secret_name,
                ),
            )

            # pvc setup
            await run_activity(
                activity=PVCSetupActivity,
                arg=PVCSetupActivityModel(
                    tenant=tenant,
                    pvc_name="practifly-pvc",
                ),
            )

            # kubernetes service
            await run_activity(
                activity=KubernetesServiceActivity,
                arg=KubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="practifly",
                    ports={"http": 8000},
                ),
            )

            # kubernetes virtual service
            await run_activity(
                activity=KubernetesIstioVirtualServiceActivity,
                arg=KubernetesIstioVirtualServiceActivityModel(
                    namespace=tenant,
                    host=f"{tenant}.api.{practifly_config.domain_name}",
                    service_name="practifly-vs",
                    payload=http_list,
                ),
            )
            one_password_vault = ProductEnum.get_onepassword_vault_name(ProductEnum.practifly)
            # insert fernet key into 1Password if it doesn't exist
            fernet_key = Fernet.generate_key().decode()
            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=tenant,
                    vault=one_password_vault,
                    server_item=f"practifly-tenant-config-{config.env.lower().strip()}",
                    key="fernet_key",
                    key_value=fernet_key,
                ),
            )

            common_config = "common-config.json"
            env_config = "env-config.json"
            tenant_config = "tenant-config.json"
            vector_config = "vector-config.toml"
            provisioning_config = "provisioning-config.json"
            config_dir = "config"

            # kubernetes config map creation
            for config_map in [
                {
                    "name": "practifly-common-config",
                    "key": common_config,
                    "template_file_name": "common-config.tmpl.json",
                },
                {
                    "name": "practifly-env-config",
                    "key": env_config,
                    "template_file_name": f"{config.env}-env-config.tmpl.json",
                },
                {
                    "name": "practifly-tenant-config",
                    "key": tenant_config,
                    "template_file_name": f"{config.env}-tenant-config.tmpl.json",
                },
                {
                    "name": "practifly-cli-vector-config",
                    "key": vector_config,
                    "template_file_name": "vector-config.tmpl.toml",
                },
                {
                    "name": "practifly-provisioning-config",
                    "key": provisioning_config,
                    "template_file_name": f"{config.env}-provisioning-config.tmpl.json",
                },
            ]:
                await run_activity(
                    activity=K8sConfigMapCreationActivity,
                    arg=K8sConfigMapCreationActivityModel(
                        namespace=tenant,
                        name=config_map["name"],
                        template_file_name=config_map["template_file_name"],
                        cloudflare_r2_folder_path="practifly-config",
                        template_payload={
                            "tenant": tenant,
                            "orgName": organization or "Default Practice",
                        },
                        destination_file_name=config_map["key"],
                    ),
                )

            # dns setup
            await run_activity(
                activity=CreateCloudflareDNSRecordActivity,
                arg=CreateCloudflareDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{practifly_config.domain_name}",
                    zone_id=practifly_config.zone_id,
                    content=config.k8s_cname,
                ),
            )

            # create bucket
            bucket_name = f"{tenant}.{practifly_config.domain_name}"
            bucket_name = bucket_name.replace(".", "-")
            await run_activity(
                activity=CreateCloudflareBucketActivity,
                arg=CreateCloudflareBucketActivityModel(bucket_name=bucket_name),
            )

            # link bucket to custom domain
            await run_activity(
                activity=LinkBucketToDomainActivity,
                arg=LinkBucketToDomainActivityModel(
                    bucket_name=bucket_name,
                    domain_name=f"{tenant}.{practifly_config.domain_name}",
                    zone_id=practifly_config.zone_id,
                ),
            )

            # propagate the dns record
            await run_activity(
                activity=PropagateDNSRecordActivity,
                arg=PropagateDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{practifly_config.domain_name}",
                ),
            )

            # keycloak realm setup
            realm_name = f"{tenant}"
            await run_activity(
                activity=KeycloakRealmSetupActivity,
                arg=KeycloakRealmSetupActivityModel(
                    realm_name=realm_name,
                    domain=practifly_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_realm.json",
                ),
            )

            await run_activity(
                activity=KeycloakCreateTenantCustomerAdminUserActivity,
                arg=KeycloakCreateTenantCustomerAdminUserActivityModel(
                    realm_name=f"practifly_{tenant}",
                    client_name="app",
                    username=email,
                    email=email,
                    firstname=first_name,
                    lastname=last_name,
                    template_path=TemplatePath,
                    template_name="keycloak_customer_admin.json",
                ),
            )

            # keycloak tenant internal admin user setup
            await run_activity(
                activity=KeycloakCreateInternalUsersActivity,
                arg=KeycloakCreateInternalUsersActivityModel(
                    realm_name=f"practifly_{tenant}",
                    client_name="app",
                    users=[
                        {
                            "username": "admin",
                            "email": "practifly-be@314ecorp.com",
                            "firstname": "Admin",
                            "lastname": "",
                        },
                    ],
                    template_path=TemplatePath,
                    template_name="keycloak_tenant_admin.json",
                ),
            )

            # temporal namespace creation
            await run_activity(
                activity=TemporalNamespaceActivity,
                arg=TemporalNamespaceActivityModel(
                    namespace=f"practifly_{tenant}",
                ),
            )

            # vm pod scraper for server
            await run_activity(
                activity=VMPodScrapperActivity,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="practifly-metrics",
                    app="practifly",
                    path="/metrics/",
                    interval="5s",
                ),
            )

            # vm pod scraper
            await run_activity(
                activity=VMPodScrapperActivity,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="practifly-cli-metrics",
                    app="practifly-cli",
                    path="/metrics/",
                    interval="5s",
                ),
            )

            # alembic job
            await run_activity(
                activity=PractiflyJobActivity,
                arg=PractiflyJobActivityModel(
                    tenant=tenant,
                    image_tag=image_tag,
                    job_type=PractiflyJobEnum.PROVISIONING,
                ),
            )

            repo_name = "practifly-ui"
            image_tag = "production" if config.env == "production" else "sprint"

            if config.env == "production":
                dest_dir = f"{bucket_name}/"
            else:
                dest_dir = f"{bucket_name}/{image_tag}"

            src_object_name = f"{repo_name}/{image_tag}/bundle.zip"

            bundle_path = "bundle/dist"

            # copy artifacts to bucket
            await run_activity(
                activity=CopyArtifactsToBucketActivity,
                arg=CopyArtifactsToBucketActivityModel(
                    bucket_name=bucket_name,
                    src_object_name=src_object_name,
                    dest_dir=dest_dir,
                    bundle_path=bundle_path,
                    bundle_name="bundle.zip",
                    tenant=tenant,
                ),
            )

            src_object_name = f"practifly-web-core/{image_tag}/release.zip"
            web_core_bucket_name = "practifly-web-core"
            dest_dir = f"{web_core_bucket_name}/{bucket_name}"

            # copy webcore to bucket
            await run_activity(
                activity=CopyWebCoreToBucketActivity,
                arg=CopyWebCoreToBucketActivityModel(
                    src_object_name=src_object_name,
                    tenant=tenant,
                    bucket_name=web_core_bucket_name,
                    bundle_name="release.zip",
                    dest_dir=dest_dir,
                ),
            )

            # delete statefulsets
            for statefulset in ["practifly", "practifly-cli"]:
                await run_activity(
                    activity=StatefulSetPodDeletionActivity,
                    arg=StatefulSetPodDeletionActivityModel(
                        namespace=tenant,
                        name=statefulset,
                    ),
                )

            # deployment pod creation for server
            await run_activity(
                activity=KubernetesDeploymentActivity,
                arg=KubernetesDeploymentActivityModel(
                    namespace=tenant,
                    name="practifly",
                    docker_image=docker_image,
                    request_resource={
                        "cpu": pydash.get(practifly, "serverSpec.request_cpu"),
                        "memory": pydash.get(practifly, "serverSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(practifly, "serverSpec.limit_cpu"),
                        "memory": pydash.get(practifly, "serverSpec.limit_memory"),
                    },
                    container_ports={"http": 8000},
                    volume_mounts=[
                        {
                            "name": "common-volume",
                            "mount_path": f"/{config_dir}/{common_config}",
                            "sub_path": common_config,
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
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "practifly-tenant-config",
                            "key": tenant_config,
                            "path": tenant_config,
                        },
                        {
                            "name": "common-volume",
                            "config_map_name": "practifly-common-config",
                            "key": common_config,
                            "path": common_config,
                        },
                        {
                            "name": "env-volume",
                            "config_map_name": "practifly-env-config",
                            "key": env_config,
                            "path": env_config,
                        },
                        {
                            "name": "provisioning-volume",
                            "config_map_name": "practifly-provisioning-config",
                            "key": provisioning_config,
                            "path": provisioning_config,
                        },
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "APP_CONFIG_DIR", "value": f"/{config_dir}"},
                        {
                            "name": "POSTGRES__PASSWORD",
                            "value_from": {"secret_key_ref": {"name": postgres_secret_name, "key": "password"}},
                        },
                        {"name": "POSTGRES__USER", "value": postgres_username},
                        {"name": "REDIS__HOST", "value": f"cache.{tenant}.svc.cluster.local"},
                        {
                            "name": "REDIS__PASSWORD",
                            "value_from": {"secret_key_ref": {"name": redis_secret_name, "key": "password"}},
                        },
                        {"name": "RELEASE_VERSION", "value": image_tag},
                        {"name": "CLIENT_CODE", "value": tenant},
                        {"name": "IS_CLI", "value": "FALSE"},
                    ],
                ),
            )

            # statefulset pod creation for cli
            await run_activity(
                activity=KubernetesDeploymentActivity,
                arg=KubernetesDeploymentActivityModel(
                    namespace=tenant,
                    name="practifly-cli",
                    docker_image=docker_image,
                    request_resource={
                        "cpu": pydash.get(practifly, "cliSpec.request_cpu"),
                        "memory": pydash.get(practifly, "cliSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(practifly, "cliSpec.limit_cpu"),
                        "memory": pydash.get(practifly, "cliSpec.limit_memory"),
                    },
                    container_ports={"http": 8000},
                    volume_mounts=[
                        {
                            "name": "common-volume",
                            "mount_path": f"/{config_dir}/{common_config}",
                            "sub_path": common_config,
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
                            "name": "vector-volume",
                            "mount_path": "/vector",
                            "read_only": True,
                        },
                        {
                            "name": "practifly-pvc",
                            "mount_path": "/data",
                            "read_only": False,
                        },
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "practifly-tenant-config",
                            "key": tenant_config,
                            "path": tenant_config,
                        },
                        {
                            "name": "common-volume",
                            "config_map_name": "practifly-common-config",
                            "key": common_config,
                            "path": common_config,
                        },
                        {
                            "name": "env-volume",
                            "config_map_name": "practifly-env-config",
                            "key": env_config,
                            "path": env_config,
                        },
                        {
                            "name": "vector-volume",
                            "config_map_name": "practifly-cli-vector-config",
                            "key": vector_config,
                            "path": vector_config,
                        },
                        {
                            "name": "practifly-pvc",
                            "persistent_volume_claim": "practifly-pvc",
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
                        {"name": "REDIS__HOST", "value": f"cache.{tenant}.svc.cluster.local"},
                        {
                            "name": "REDIS__PASSWORD",
                            "value_from": {"secret_key_ref": {"name": redis_secret_name, "key": "password"}},
                        },
                        {"name": "RELEASE_VERSION", "value": image_tag},
                        {"name": "CLIENT_CODE", "value": tenant},
                        {"name": "IS_CLI", "value": "TRUE"},
                    ],
                ),
            )

            # check pod running status
            for pod in ["practifly", "practifly-cli"]:
                await run_activity(
                    activity=CheckPodRunningStatusActivity,
                    arg=CheckPodRunningStatusActivityModel(
                        namespace=tenant,
                        name=pod,
                    ),
                )

            # update tenant status
            await run_activity(
                activity=UpdateTenantStatusActivity,
                arg=TenantCliStatus(
                    tenant_name=tenant, status=TenantStatusEnum.Provisioned, product=ProductEnum.practifly
                ),
            )

            # send mail
            await run_activity(
                activity=SendAfterProvisioningMailActivity,
                arg=SendAfterProvisioningMailActivityModel(
                    realm_name=f"practifly_{tenant}",
                    tenant=tenant,
                    user_details={
                        "firstName": first_name,
                        "lastName": last_name,
                        "email": email,
                    },
                    domain_name=practifly_config.domain_name,
                    product=ProductName,
                    from_name=practifly_config.sender_name,
                    email_from=practifly_config.sender_email,
                ),
            )

            # create tenant crd
            await run_activity(
                activity=TenantCrdCreationActivity,
                arg=TenantCrdCreationActivityModel(
                    tenant=tenant,
                    kind=ResourceKindEnum.PractiflyTenant,
                    product=ProductName,
                    data=ijson_dumps(practifly),
                ),
            )

        except Exception as e:
            workflow.logger.error(f"Error in onboarding workflow: {e}")
            await run_activity(
                activity=UpdateTenantStatusActivity,
                arg=TenantCliStatus(
                    tenant_name=tenant,
                    status=TenantStatusEnum.ProvisioningFailed,
                    error_msg=str(e),
                    product=ProductEnum.practifly,
                ),
            )
            raise e

    @workflow.signal
    async def approve(self: "Workflow") -> None:
        """
        Approve the workflow
        """
        self.approved = True

    @workflow.signal
    async def decline(self: "Workflow") -> None:
        """
        Deny the workflow
        """
        self.denied = True
