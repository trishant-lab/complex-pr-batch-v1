from collections.abc import Callable
from datetime import timedelta

from app.cli.temporal.activities.cloudflare_setup import (
    CopyArtifactsToBucketActivity,
    CreateCloudflareBucketActivity,
    CreateCloudflareBucketCredentialsActivity,
    CreateCloudflareDNSRecordActivity,
    LinkBucketToDomainActivity,
    PropagateDNSRecordActivity,
    UpdateCORSForBucketActivity,
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
from app.cli.temporal.activities.k8s_service import KubernetesServiceActivity, KubernetesServiceActivityModel
from app.cli.temporal.activities.muspell_configupdate_job import (
    MuspellConfigUpdateJobActivity,
    MuspellConfigUpdateJobActivityModel,
)
from app.cli.temporal.activities.redis import RedisSetupActivity, RedisSetupActivityModel
from app.cli.temporal.activities.send_mail import (
    SendAfterProvisioningMailActivity,
    SendAfterProvisioningMailActivityModel,
)
from app.cli.temporal.activities.starrocks_setup import CreateStarRocksCatalogActivity, CreateStarRocksUserActivity
from app.cli.temporal.activities.stateful_set_pod_creation import (
    CheckPodRunningStatusActivity,
    CheckPodRunningStatusActivityModel,
)
from app.cli.temporal.activities.vm_pod_scrapper import VMPodScrapperActivity, VMPodScrapperActivityModel
from app.cli.temporal.core.log import log_info
from app.cli.temporal.models.cloudflare import (
    CloudflareBucketCredentials,
    CopyArtifactsToBucketActivityModel,
    CreateCloudflareBucketActivityModel,
    CreateCloudflareBucketCredentialsActivityModel,
    CreateCloudflareDNSRecordActivityModel,
    LinkBucketToDomainActivityModel,
    PropagateDNSRecordActivityModel,
    UpdateCORSForBucketActivityModel,
)
from app.cli.temporal.models.starrocks import CreateStarRocksCatalogActivityModel
from app.cli.temporal.muspell import TemplatePath
from app.cli.activity_util import run_activity
from app.cli.temporal.activities.k8s_namespace import K8sNamespaceCreationActivity, K8sNamespaceCreationActivityModel
from app.cli.temporal.activities.k8s_secret import K8sSecretCreationActivity, K8sSecretCreationActivityModel
from app.cli.temporal.activities.keycloak_setup import (
    KeycloakClientSetupActivity,
    KeycloakClientSetupActivityModel,
    KeycloakCreateClientRolesActivity,
    KeycloakCreateClientRolesActivityModel,
    KeycloakCreateInternalUsersActivity,
    KeycloakCreateInternalUsersActivityModel,
    KeycloakCreateTenantCustomerAdminUserActivity,
    KeycloakCreateTenantCustomerAdminUserActivityModel,
    KeycloakRealmSetupActivity,
    KeycloakRealmSetupActivityModel,
)
from app.cli.temporal.activities.one_password import (
    OnePasswordCreateOrUpdateActivity,
    OnePasswordCreateOrUpdateActivityModel,
    OnePasswordInsertIfNotExistsActivity,
    OnePasswordInsertIfNotExistsActivityModel,
)
from app.cli.temporal.activities.postgres_setup import (
    KeycloakUserMappingActivity,
    KeycloakUserMappingActivityModel,
    PostgresGrantAccessToUserActivity,
    PostgresGrantAccessToUserActivityModel,
    PostgresGrantAllPrivilegesOnTableActivity,
    PostgresGrantAllPrivilegesOnTableActivityModel,
    PostgresSchemaCreationActivity,
    PostgresSchemaCreationActivityModel,
    PostgresUserCreationActivity,
    PostgresUserCreationActivityModel,
)
from app.cli.temporal.activities.update_tenant_status import TenantCliStatus, UpdateTenantStatusActivity
from app.cli.temporal.core.base import Workflow
from app.cli.temporal.muspell.models.muspellSpec import MuspellArchiveSpec
from app.common import generate_password
from app.core.ijson import ijson_dumps, ijson_loads

from typing import TYPE_CHECKING

from app.starrocks_utils import RegisterStarrocksUserModel

if TYPE_CHECKING:
    from app.core.product_settings.muspell_archive import MuspellArchiveSettings
from app.core.settings import AppSettings, get_settings
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum
import pydash
from temporalio import workflow

from app.template_env import get_env

ProductName = "muspell"
OnePasswordVaultName = "Muspell Archive"


@workflow.defn(name="MuspellOnboardingWorkflow", sandboxed=False)
class MuspellOnboardingWorkflow(Workflow):
    """
    Muspell Archive Onboarding Workflow
    """

    def __init__(self: "Workflow") -> None:
        self.approved: bool = False
        self.deny: bool = False

    @staticmethod
    def get_activities() -> list[type[Callable]]:
        """
        Return list of activities used in the workflow
        """
        return [
            SendAfterProvisioningMailActivity.defn,
            UpdateTenantStatusActivity.defn,
            PostgresUserCreationActivity.defn,
            PostgresSchemaCreationActivity.defn,
            PostgresGrantAccessToUserActivity.defn,
            KeycloakUserMappingActivity.defn,
            K8sNamespaceCreationActivity.defn,
            K8sSecretCreationActivity.defn,
            KeycloakRealmSetupActivity.defn,
            KeycloakClientSetupActivity.defn,
            KeycloakCreateClientRolesActivity.defn,
            KeycloakCreateTenantCustomerAdminUserActivity.defn,
            CreateStarRocksCatalogActivity.defn,
            KubernetesDeploymentActivity.defn,
            KubernetesIstioVirtualServiceActivity.defn,
            KubernetesServiceActivity.defn,
            K8sConfigMapCreationActivity.defn,
            OnePasswordCreateOrUpdateActivity.defn,
            CheckPodRunningStatusActivity.defn,
            CreateCloudflareBucketActivity.defn,
            CreateCloudflareDNSRecordActivity.defn,
            LinkBucketToDomainActivity.defn,
            PropagateDNSRecordActivity.defn,
            CopyArtifactsToBucketActivity.defn,
            PostgresGrantAllPrivilegesOnTableActivity.defn,
            VMPodScrapperActivity.defn,
            CreateStarRocksUserActivity.defn,
            RedisSetupActivity.defn,
            UpdateCORSForBucketActivity.defn,
            CreateCloudflareBucketCredentialsActivity.defn,
            OnePasswordInsertIfNotExistsActivity.defn,
            MuspellConfigUpdateJobActivity.defn,
            KeycloakCreateInternalUsersActivity.defn,
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", muspell: MuspellArchiveSpec) -> str:
        """
        Return workflow id
        """
        return f"muspell_onboarding_workflow_{pydash.get(muspell, 'tenant')}"

    @workflow.run
    async def run(self: "Workflow", muspell: MuspellArchiveSpec) -> None:
        """
        Run workflow
        """
        config: AppSettings = get_settings()
        muspell_config: MuspellArchiveSettings = config.muspell

        first_name = pydash.get(muspell, "firstName")
        last_name = pydash.get(muspell, "lastName")
        email = pydash.get(muspell, "email")
        tenant = pydash.get(muspell, "tenant")
        application_list_str = pydash.get(muspell, "applicationList")
        enable_mpi = pydash.get(muspell, "enableMpi")
        application_list = (
            [item.strip() for item in application_list_str.split(",") if item.strip()] if application_list_str else []
        )
        log_info(f"Application list: {application_list}")

        try:
            await workflow.wait_condition(lambda: self.approved or self.deny)

            if self.deny:
                await run_activity(
                    activity=UpdateTenantStatusActivity,
                    arg=TenantCliStatus(
                        tenant_name=pydash.get(muspell, "tenant"),
                        status=TenantStatusEnum.Declined,
                        error_msg="Request Declined",
                        product=ProductEnum.muspell,
                    ),
                    start_to_close_timeout=timedelta(seconds=120),
                )
                return

            postgres_schema_name = tenant
            postgres_database_name = "muspell"
            postgres_username = f"{ProductName}_{tenant}"
            postgres_password = generate_password(length=20)
            image_tag = "production" if config.env == "production" else "sprint"
            docker_image = f"registry.314ecorp.tech/muspell-app:{image_tag}"
            server_item = "production-config" if config.env == "production" else "integration-config"

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item=server_item,
                    vault=OnePasswordVaultName,
                    secret_name="pg_username",
                    secret_value=postgres_username,
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item=server_item,
                    vault=OnePasswordVaultName,
                    secret_name="pg_password",
                    secret_value=postgres_password,
                ),
            )

            await run_activity(
                activity=PostgresUserCreationActivity,
                arg=PostgresUserCreationActivityModel(
                    username=postgres_username,
                    database_name=postgres_database_name,
                    password=postgres_password,
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

            await run_activity(
                activity=KeycloakUserMappingActivity,
                arg=KeycloakUserMappingActivityModel(
                    username=postgres_username,
                    database_name=postgres_database_name,
                ),
            )

            await run_activity(
                activity=PostgresGrantAllPrivilegesOnTableActivity,
                arg=PostgresGrantAllPrivilegesOnTableActivityModel(
                    database_name=postgres_database_name,
                    username=postgres_username,
                    tables=[
                        "user_entity",
                        "realm",
                        "user_attribute",
                        "keycloak_role",
                        "keycloak_group",
                        "user_role_mapping",
                        "federated_identity",
                        "user_group_membership",
                    ],
                ),
            )

            await run_activity(
                activity=K8sNamespaceCreationActivity,
                arg=K8sNamespaceCreationActivityModel(namespace=tenant),
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

            # secret setup for redis password
            await run_activity(
                activity=K8sSecretCreationActivity,
                arg=K8sSecretCreationActivityModel(
                    namespace=tenant,
                    name="cache-secret",
                    string_data={"REDIS_PASSWORD": config.cache_admin_password},
                ),
            )

            redis_tenant_password = generate_password(length=20)

            await run_activity(
                activity=RedisSetupActivity,
                arg=RedisSetupActivityModel(
                    namespace=tenant,
                    product=ProductName,
                    redis_tenant_password=redis_tenant_password,
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item=server_item,
                    vault=OnePasswordVaultName,
                    secret_name="redis_password",
                    secret_value=redis_tenant_password,
                ),
            )

            # dns setup for api
            await run_activity(
                activity=CreateCloudflareDNSRecordActivity,
                arg=CreateCloudflareDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{muspell_config.domain_name}",
                    zone_id=muspell_config.zone_id,
                    content=config.k8s_cname,
                ),
            )

            # create bucket
            bucket_name = f"{tenant}-{muspell_config.domain_name.replace('.', '-')}"
            await run_activity(
                activity=CreateCloudflareBucketActivity,
                arg=CreateCloudflareBucketActivityModel(bucket_name=bucket_name),
            )

            # link bucket to custom domain
            await run_activity(
                activity=LinkBucketToDomainActivity,
                arg=LinkBucketToDomainActivityModel(
                    bucket_name=bucket_name,
                    domain_name=f"{tenant}.{muspell_config.domain_name}",
                    zone_id=muspell_config.zone_id,
                ),
            )

            # update cors for bucket
            await run_activity(
                activity=UpdateCORSForBucketActivity,
                arg=UpdateCORSForBucketActivityModel(
                    bucket_name=bucket_name,
                    rules=[
                        {
                            "allowed": {
                                "methods": ["GET", "PUT", "HEAD", "POST", "DELETE"],
                                "origins": ["*"],
                                "headers": [
                                    "Authorization",
                                    "content-type",
                                    "x-amz-*",
                                    "traceparent",
                                    "x-highlight-request",
                                    "X-LOGINSERVICEAREA",
                                ],
                            },
                            "exposeHeaders": ["ETag", "Location", "Content-Disposition"],
                        }
                    ],
                ),
            )

            # ui setup
            repo_name = "muspell-ui"
            image_tag = "production" if config.env == "production" else "sprint"

            if config.env == "production":
                dest_dir = f"{bucket_name}/"
            else:
                dest_dir = f"{bucket_name}/{image_tag}"

            src_object_name = f"{repo_name}/{image_tag}/bundle.zip"

            bundle_path = "bundle/dist"

            if muspell_config.copy_ui_bundle:
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
                    retry_policy=CopyArtifactsToBucketActivity.get_retry_policy(),
                    start_to_close_timeout=CopyArtifactsToBucketActivity.get_timeout(),
                )

            credentials: CloudflareBucketCredentials = await run_activity(
                activity=CreateCloudflareBucketCredentialsActivity,
                arg=CreateCloudflareBucketCredentialsActivityModel(bucket_name=bucket_name, read_only=False),
            )

            # cdn base url added to onepassword
            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item=server_item,
                    key="base_url_cdn",
                    key_value=f"https://{tenant}.{muspell_config.domain_name}",
                ),
            )

            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item=server_item,
                    key="keycloak_auth_url",
                    key_value=f"https://{tenant}.{muspell_config.domain_name}",
                ),
            )

            # s3 bucket name added to onepassword
            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item=server_item,
                    key="s3_bucket_name",
                    key_value=bucket_name,
                ),
            )

            # s3 access key added to onepassword
            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item=server_item,
                    key="s3_access_key",
                    key_value=credentials.access_key,
                ),
            )

            # s3 secret key added to onepassword
            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item=server_item,
                    key="s3_secret_key",
                    key_value=credentials.secret_key,
                ),
            )

            realm_name = tenant
            # keycloak realm setup
            await run_activity(
                activity=KeycloakRealmSetupActivity,
                arg=KeycloakRealmSetupActivityModel(
                    realm_name=realm_name,
                    domain=muspell_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_realm.json",
                ),
            )

            # keycloak client setup
            await run_activity(
                activity=KeycloakClientSetupActivity,
                arg=KeycloakClientSetupActivityModel(
                    tenant=tenant,
                    realm_name=realm_name,
                    domain=muspell_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_muspell_client.json",
                ),
            )

            roles = [
                "_can-access-patient-list",
                "_can-bypass-break-the-glass",
                "_can-control-access",
                "_can-create-edit-value-sets",
                "_can-launch-standalone",
                "_can-manage-streamline",
                "_can-merge-patient",
                "_can-purge-patient",
                "_can-release-information",
                "_can-save-document",
                "_can-share-feedback",
                "_can-upload-and-delete-documents",
                "_can-view-admin-settings",
                "_can-view-application-settings",
                "_can-view-reports",
                "_can-view-ssn",
                "_can-view-value-sets",
                "_developer",
                "_superset_Admin_CreateEditReports",
                "_superset_Admin_DeleteReports",
                "_superset_Admin_EngineerSQL",
                "_superset_Admin_ExportReports",
                "_superset_ViewReports",
            ]

            # keycloak client roles setup
            await run_activity(
                activity=KeycloakCreateClientRolesActivity,
                arg=KeycloakCreateClientRolesActivityModel(
                    client_name="muspell",
                    realm_name=realm_name,
                    roles=roles,
                ),
            )

            template_env = get_env(template_path=TemplatePath)

            applicationaccess = None

            if application_list:
                applicationaccess_template = template_env.get_template("applicationaccess.json")
                applicationaccess_json = applicationaccess_template.render(application_list=application_list)
                applicationaccess = ijson_dumps(applicationaccess_json)

            # keycloak tenant customer admin user setup
            await run_activity(
                activity=KeycloakCreateTenantCustomerAdminUserActivity,
                arg=KeycloakCreateTenantCustomerAdminUserActivityModel(
                    realm_name=realm_name,
                    client_name="muspell",
                    username=email,
                    email=email,
                    firstname=first_name,
                    lastname=last_name,
                    template_path=TemplatePath,
                    template_name="keycloak_tenant_customer_admin.json",
                    template_payload={"applicationaccess": applicationaccess} if applicationaccess else None,
                    roles=[role for role in roles if role != "_developer"],
                ),
            )

            await run_activity(
                activity=KeycloakCreateInternalUsersActivity,
                arg=KeycloakCreateInternalUsersActivityModel(
                    realm_name=realm_name,
                    client_name="muspell",
                    template_path=TemplatePath,
                    template_name="keycloak_tenant_internal_user.json",
                    users=[
                        {
                            "username": "vaishnavi.sharma@314ecorp.com",
                            "email": "vaishnavi.sharma@314ecorp.com",
                            "firstname": "Vaishnavi",
                            "lastname": "Sharma",
                        },
                        {
                            "username": "soumya.agarwal@314ecorp.com",
                            "email": "soumya.agarwal@314ecorp.com",
                            "firstname": "Soumya",
                            "lastname": "Agrawal",
                        },
                    ],
                    template_payload={"applicationaccess": applicationaccess} if applicationaccess else None,
                    roles=[role for role in roles if role != "_developer"],
                ),
            )

            # Create the StarRocks catalog
            await run_activity(
                activity=CreateStarRocksCatalogActivity,
                arg=CreateStarRocksCatalogActivityModel(
                    tenant=tenant,
                    catalog_name=tenant,
                    warehouse_access_key=muspell_config.warehouse_access_key,
                    warehouse_secret_key=muspell_config.warehouse_secret_key,
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item=server_item,
                    secret_name="catalog",
                    secret_value=tenant,
                ),
            )

            starrocks_username = f"{ProductName}_{tenant}"
            starrocks_password = generate_password(length=20)

            # Create the StarRocks catalog
            await run_activity(
                activity=CreateStarRocksUserActivity,
                arg=RegisterStarrocksUserModel(
                    muspell_config=muspell_config,
                    tenant=tenant,
                    catalog_name=tenant,
                    user_name=starrocks_username,
                    user_password=starrocks_password,
                ),
            )

            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item=server_item,
                    key="sr_username",
                    key_value=starrocks_username,
                ),
            )

            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item=server_item,
                    key="sr_password",
                    key_value=starrocks_password,
                ),
            )

            tenant_config = f"{config.env}.toml"
            code_system_config = "code_systems.toml"
            config_dir = "app/config"

            # setup tenant configmap
            for config_map in [
                {
                    "name": "muspell-config",
                    "key": tenant_config,
                    "template_file_name": f"{config.env}-tenant-config.tmpl.toml",
                },
                {
                    "name": "muspell-config-system",
                    "key": code_system_config,
                    "template_file_name": f"{config.env}-tenant-system.tmpl.toml",
                },
            ]:
                await run_activity(
                    activity=K8sConfigMapCreationActivity,
                    arg=K8sConfigMapCreationActivityModel(
                        namespace=tenant,
                        name=config_map["name"],
                        template_file_name=config_map["template_file_name"],
                        destination_file_name=config_map["key"],
                        cloudflare_r2_folder_path="muspell-config",
                        template_payload={"tenant": tenant, "enableMPI": enable_mpi},
                    ),
                )

            # kubernetes service
            await run_activity(
                activity=KubernetesServiceActivity,
                arg=KubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="muspell-archive",
                    ports={"http": 8080},
                ),
            )

            template = template_env.get_template("istio-rules.json")
            output = template.render(tenant=tenant, image_tag=image_tag, env=config.env)

            http_list = ijson_loads(output)
            if config.env != "production":
                http_list.append(
                    {
                        "name": "redirect",
                        "match": [{"uri": {"exact": "/"}}],
                        "redirect": {"uri": f"/{image_tag}/"},
                    }
                )

            # kubernetes virtual service
            await run_activity(
                activity=KubernetesIstioVirtualServiceActivity,
                arg=KubernetesIstioVirtualServiceActivityModel(
                    namespace=tenant,
                    host=f"{tenant}.api.{muspell_config.domain_name}",
                    service_name="muspell-vs",
                    payload=http_list,
                ),
            )

            # statefulset pod creation for server
            await run_activity(
                activity=KubernetesDeploymentActivity,
                arg=KubernetesDeploymentActivityModel(
                    namespace=tenant,
                    name="muspell-archive",
                    docker_image=docker_image,
                    request_resource={
                        "cpu": pydash.get(muspell, "serverSpec.request_cpu"),
                        "memory": pydash.get(muspell, "serverSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(muspell, "serverSpec.limit_cpu"),
                        "memory": pydash.get(muspell, "serverSpec.limit_memory"),
                    },
                    container_ports={"http": 8080},
                    volume_mounts=[
                        {
                            "name": "muspell-config",
                            "mount_path": f"/{config_dir}/{tenant_config}",
                            "sub_path": tenant_config,
                        },
                        {
                            "name": "muspell-config-system",
                            "mount_path": f"/{config_dir}/{code_system_config}",
                            "sub_path": code_system_config,
                        },
                    ],
                    volumes=[
                        {
                            "name": "muspell-config",
                            "config_map_name": "muspell-config",
                            "key": tenant_config,
                            "path": tenant_config,
                        },
                        {
                            "name": "muspell-config-system",
                            "config_map_name": "muspell-config-system",
                            "key": code_system_config,
                            "path": code_system_config,
                        },
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {
                            "name": "DATABASE_URL",
                            "value": (
                                f"postgresql://{postgres_username}:{postgres_password}"
                                "@db-cluster-ha.postgresql.svc.cluster.local:5432"
                                "/muspell?sslmode=disable&application_name=muspell&options=-c "
                                f"search_path%3D{postgres_schema_name},public"
                            ),
                        },
                    ],
                ),
            )

            # vm pod scraper
            await run_activity(
                activity=VMPodScrapperActivity,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="muspell-metrics",
                    app="muspell-archive",
                    path="/metrics/",
                    interval="15s",
                ),
            )

            # propagate the dns record
            await run_activity(
                activity=PropagateDNSRecordActivity,
                arg=PropagateDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{muspell_config.domain_name}",
                ),
            )

            # check pod running status
            await run_activity(
                activity=CheckPodRunningStatusActivity,
                arg=CheckPodRunningStatusActivityModel(
                    namespace=tenant,
                    name="muspell-archive",
                ),
                retry_policy=CheckPodRunningStatusActivity.get_retry_policy(),
                start_to_close_timeout=CheckPodRunningStatusActivity.get_timeout(),
            )

            if application_list:
                # Read column config and update the same in Postgres.
                col_template = template_env.get_template("column_config.json")
                output = col_template.render(application_list=application_list)
                column_config = ijson_loads(output)

                org_template = template_env.get_template("organization_config.json")
                output = org_template.render(application_list=application_list)
                organization_config = ijson_loads(output)

                # update the config in Postgres
                await run_activity(
                    activity=MuspellConfigUpdateJobActivity,
                    arg=MuspellConfigUpdateJobActivityModel(
                        column_config=column_config,
                        organization_config=organization_config,
                        schema_name=postgres_schema_name,
                        database_name=postgres_database_name,
                        username=postgres_username,
                        password=postgres_password,
                    ),
                )

            if config.env != "production":
                # create bucket
                r2_bucket_name = f"ma-{tenant}"
                await run_activity(
                    activity=CreateCloudflareBucketActivity,
                    arg=CreateCloudflareBucketActivityModel(bucket_name=r2_bucket_name),
                )

                r2_credentials: CloudflareBucketCredentials = await run_activity(
                    activity=CreateCloudflareBucketCredentialsActivity,
                    arg=CreateCloudflareBucketCredentialsActivityModel(bucket_name=r2_bucket_name, read_only=False),
                )

                # r2 access key added to onepassword
                await run_activity(
                    activity=OnePasswordInsertIfNotExistsActivity,
                    arg=OnePasswordInsertIfNotExistsActivityModel(
                        tenant=f"{ProductName}_{tenant}",
                        vault=OnePasswordVaultName,
                        server_item=server_item,
                        key="r2_documents_access_key",
                        key_value=r2_credentials.access_key,
                    ),
                )

                # r2 secret key added to onepassword
                await run_activity(
                    activity=OnePasswordInsertIfNotExistsActivity,
                    arg=OnePasswordInsertIfNotExistsActivityModel(
                        tenant=f"{ProductName}_{tenant}",
                        vault=OnePasswordVaultName,
                        server_item=server_item,
                        key="r2_documents_secret_key",
                        key_value=r2_credentials.secret_key,
                    ),
                )

                # r2 endpoint added to onepassword
                await run_activity(
                    activity=OnePasswordInsertIfNotExistsActivity,
                    arg=OnePasswordInsertIfNotExistsActivityModel(
                        tenant=f"{ProductName}_{tenant}",
                        vault=OnePasswordVaultName,
                        server_item=server_item,
                        key="r2_endpoint",
                        key_value=config.cloudflare.r2_endpoint,
                    ),
                )

                # Create pipeline for ETL job

            # update tenant status
            await run_activity(
                activity=UpdateTenantStatusActivity,
                arg=TenantCliStatus(
                    tenant_name=tenant, status=TenantStatusEnum.Provisioned, product=ProductEnum.muspell
                ),
            )

            # send mail
            await run_activity(
                activity=SendAfterProvisioningMailActivity,
                arg=SendAfterProvisioningMailActivityModel(
                    realm_name=realm_name,
                    tenant=tenant,
                    user_details={
                        "firstName": first_name,
                        "lastName": last_name,
                        "email": email,
                    },
                    domain_name=muspell_config.domain_name,
                    product=ProductName,
                    from_name=muspell_config.sender_name,
                    email_from=muspell_config.sender_email,
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
                    product=ProductEnum.muspell,
                ),
                start_to_close_timeout=timedelta(seconds=120),
            )
            raise e

    @workflow.signal
    async def approve(self: "Workflow") -> None:
        """
        Signal to approve the workflow
        """
        self.approved = True

    @workflow.signal
    async def deny(self: "Workflow") -> None:
        """
        Signal to reject the workflow
        """
        self.deny = True
