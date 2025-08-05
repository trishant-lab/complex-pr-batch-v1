from collections.abc import Callable

import pydash
from temporalio import workflow

from app.cli.activity_util import run_activity
from app.cli.temporal.activities.cloudflare_setup import (
    CopyArtifactsToBucketActivity,
    CreateCloudflareBucketActivity,
    CreateCloudflareBucketCredentialsActivity,
    CreateCloudflareDNSRecordActivity,
    LinkBucketToDomainActivity,
    PropagateDNSRecordActivity,
    UpdateCORSForBucketActivity,
)
from app.cli.temporal.activities.database_migration_job import (
    DatabaseMigrationJobActivity,
    DatabaseMigrationJobActivityModel,
)
from app.cli.temporal.activities.deployment_pod_creation import (
    KubernetesDeploymentActivity,
    KubernetesDeploymentActivityModel,
)
from app.cli.temporal.activities.dexit_novu_setup import DexitNovuSetupActivity
from app.cli.temporal.activities.dexit_zsegment_creation import ZSegmentSetupActivity
from app.cli.temporal.activities.fax_setup import FaxSetupActivity
from app.cli.temporal.activities.k8s_config_map import K8sConfigMapCreationActivity, K8sConfigMapCreationActivityModel
from app.cli.temporal.activities.k8s_istio_virtual_service import (
    KubernetesIstioVirtualServiceActivity,
    KubernetesIstioVirtualServiceActivityModel,
)
from app.cli.temporal.activities.k8s_namespace import (
    K8sNamespaceCreationActivity,
    K8sNamespaceCreationActivityModel,
)
from app.cli.temporal.activities.k8s_secret import (
    K8sSecretCreationActivity,
    K8sSecretCreationActivityModel,
)
from app.cli.temporal.activities.k8s_service import (
    KubernetesServiceActivity,
    KubernetesServiceActivityModel,
)
from app.cli.temporal.activities.keycloak_setup import (
    DexitKeycloakCreateIDPFlowActivity,
    KeycloakClientSetupActivity,
    KeycloakClientSetupActivityModel,
    KeycloakCreateClientRolesActivity,
    KeycloakCreateClientRolesActivityModel,
    KeycloakCreateTenantCustomerAdminUserActivity,
    KeycloakCreateTenantCustomerAdminUserActivityModel,
    KeycloakRealmSetupActivity,
    KeycloakRealmSetupActivityModel,
    KeycloakServiceAccountSetupActivity,
    KeycloakServiceAccountSetupActivityModel,
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
    MatomoUserMappingActivity,
    MatomoUserMappingActivityModel,
    PostgresDatabaseCreationActivity,
    PostgresDatabaseCreationActivityModel,
    PostgresGrantAccessToUserActivity,
    PostgresGrantAccessToUserActivityModel,
    PostgresGrantAllPrivilegesOnTableActivity,
    PostgresGrantAllPrivilegesOnTableActivityModel,
    PostgresSchemaCreationActivity,
    PostgresSchemaCreationActivityModel,
    PostgresSupavisorPollUserActivity,
    PostgresSupavisorPollUserActivityModel,
    PostgresUserCreationActivity,
    PostgresUserCreationActivityModel,
)
from app.cli.temporal.activities.stateful_set_pod_creation import (
    CheckPodRunningStatusActivity,
    CheckPodRunningStatusActivityModel,
)
from app.cli.temporal.activities.temporal_namespace import (
    TemporalNamespaceActivity,
    TemporalNamespaceActivityModel,
)
from app.cli.temporal.activities.temporal_search_atrributes_creation import (
    TemporalSearchAttributesCreationActivity,
    TemporalSearchAttributesCreationActivityModel,
)
from app.cli.temporal.activities.vm_pod_scrapper import (
    VMPodScrapperActivity,
    VMPodScrapperActivityModel,
)
from app.cli.temporal.core.base import Workflow
from app.cli.temporal.dexit import TemplatePath
from app.cli.temporal.dexit.models.dexit_spec import DexitSpec
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
from app.cli.temporal.zsegment.models.zsegment_spec import ZSegmentSpec
from app.common import generate_password
from app.core.ijson import ijson_loads
from app.core.settings import AppSettings, DexitSettings, get_settings
from app.template_env import get_env

ProductName = "dexit"
OnePasswordVaultName = "Dexit"


@workflow.defn(name="DexitDeploymentWorkflow", sandboxed=False)
class DexitDeploymentWorkflow(Workflow):
    """
    Dexit Deployment Workflow
    """

    @staticmethod
    def get_activities() -> list[type[Callable]]:
        """
        Return list of activities used in the workflow
        """
        return [
            PostgresUserCreationActivity.defn,
            PostgresSchemaCreationActivity.defn,
            PostgresGrantAccessToUserActivity.defn,
            KeycloakUserMappingActivity.defn,
            MatomoUserMappingActivity.defn,
            PostgresGrantAllPrivilegesOnTableActivity.defn,
            K8sNamespaceCreationActivity.defn,
            K8sSecretCreationActivity.defn,
            DatabaseMigrationJobActivity.defn,
            DexitNovuSetupActivity.defn,
            KeycloakRealmSetupActivity.defn,
            KeycloakClientSetupActivity.defn,
            KeycloakCreateClientRolesActivity.defn,
            KeycloakCreateTenantCustomerAdminUserActivity.defn,
            KubernetesDeploymentActivity.defn,
            VMPodScrapperActivity.defn,
            KubernetesIstioVirtualServiceActivity.defn,
            KubernetesServiceActivity.defn,
            K8sConfigMapCreationActivity.defn,
            TemporalNamespaceActivity.defn,
            TemporalSearchAttributesCreationActivity.defn,
            FaxSetupActivity.defn,
            OnePasswordCreateOrUpdateActivity.defn,
            PostgresDatabaseCreationActivity.defn,
            KeycloakServiceAccountSetupActivity.defn,
            CheckPodRunningStatusActivity.defn,
            CreateCloudflareBucketActivity.defn,
            CreateCloudflareDNSRecordActivity.defn,
            LinkBucketToDomainActivity.defn,
            PropagateDNSRecordActivity.defn,
            CopyArtifactsToBucketActivity.defn,
            PostgresSupavisorPollUserActivity.defn,
            DexitKeycloakCreateIDPFlowActivity.defn,
            ZSegmentSetupActivity.defn,
            CreateCloudflareBucketCredentialsActivity.defn,
            UpdateCORSForBucketActivity.defn,
            OnePasswordInsertIfNotExistsActivity.defn,
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", dexit: DexitSpec) -> str:
        """
        Return workflow id
        """
        return f"dexit_onboarding_workflow_{pydash.get(dexit, 'tenant')}"

    @workflow.run
    async def run(self: "Workflow", dexit: DexitSpec) -> None:
        """
        Run workflow
        """
        config: AppSettings = get_settings()
        dexit_config: DexitSettings = config.dexit

        first_name = pydash.get(dexit, "firstName")
        last_name = pydash.get(dexit, "lastName")
        email = pydash.get(dexit, "email")
        tenant = pydash.get(dexit, "tenant")

        try:
            postgres_schema_name = tenant
            postgres_database_name = "dexit"
            postgres_username = f"{ProductName}_{tenant}"
            postgres_password = generate_password(length=20)
            dicom_database_name = f"{ProductName}_dicom_{tenant}"
            dicom_database_password = generate_password(length=20)
            image_tag = "production" if config.env == "production" else "sprint"
            docker_image = f"registry.314ecorp.tech/dexit-app:{image_tag}"
            server_item = "production-config" if config.env == "production" else "integration-config"

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=tenant,
                    server_item=server_item,
                    vault=OnePasswordVaultName,
                    secret_name="pg_dicom_password",
                    secret_value=dicom_database_password,
                ),
            )

            # create postgres database for dicom
            await run_activity(
                activity=PostgresDatabaseCreationActivity,
                arg=PostgresDatabaseCreationActivityModel(
                    database_name=dicom_database_name,
                ),
            )

            # create postgres user for dicom
            await run_activity(
                activity=PostgresUserCreationActivity,
                arg=PostgresUserCreationActivityModel(
                    username=dicom_database_name,
                    database_name=dicom_database_name,
                    password=dicom_database_password,
                ),
            )

            await run_activity(
                activity=PostgresGrantAccessToUserActivity,
                arg=PostgresGrantAccessToUserActivityModel(
                    username=dicom_database_name,
                    database_name=dicom_database_name,
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=tenant,
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

            await run_activity(
                activity=KeycloakUserMappingActivity,
                arg=KeycloakUserMappingActivityModel(
                    username=postgres_username,
                    database_name=postgres_database_name,
                ),
            )

            await run_activity(
                activity=MatomoUserMappingActivity,
                arg=MatomoUserMappingActivityModel(
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
                        "user_role_mapping",
                        "matomo_log_visit",
                        "matomo_log_action",
                        "matomo_log_media",
                        "matomo_log_link_visit_action",
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

            # setup novu
            await run_activity(activity=DexitNovuSetupActivity, arg=dexit)

            # fax setup
            await run_activity(activity=FaxSetupActivity, arg=dexit)

            realm_name = tenant
            # keycloak realm setup
            await run_activity(
                activity=KeycloakRealmSetupActivity,
                arg=KeycloakRealmSetupActivityModel(
                    realm_name=realm_name,
                    domain=dexit_config.domain_name,
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
                    domain=dexit_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_dexit_client.json",
                ),
            )

            roles = [
                "_standalone-launch",
                "_document-read",
                "_delete-document",
                "_document-indexing",
                "_document-commit",
                "_manage-document-type",
                "_manage-deficiency",
                "_manage-users",
                "_manage-organisation",
                "_manage-document-type",
                "_manage-document-type",
                "_manage-queues",
                "_manage-subscription",
                "_manage-faxes",
                "_manage-bulk-import",
                "_roi",
                "_reports",
                "_document-review",
                "_manage-workflow",
                "_internal-admin",
            ]

            # keycloak client roles setup
            await run_activity(
                activity=KeycloakCreateClientRolesActivity,
                arg=KeycloakCreateClientRolesActivityModel(
                    client_name="dexit",
                    realm_name=realm_name,
                    roles=roles,
                ),
            )

            # Create Service account
            client_secret = generate_password(length=32)

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=tenant,
                    server_item=server_item,
                    vault=OnePasswordVaultName,
                    secret_name="service_account_secret",
                    secret_value=client_secret,
                ),
            )

            await run_activity(
                activity=KeycloakServiceAccountSetupActivity,
                arg=KeycloakServiceAccountSetupActivityModel(
                    tenant=tenant,
                    domain=dexit_config.domain_name,
                    secret=client_secret,
                    realm_name=realm_name,
                    template_path=TemplatePath,
                    template_name="keycloak_service_account.json",
                ),
            )

            # Create IDP mappers
            await workflow.execute_activity(
                activity=DexitKeycloakCreateIDPFlowActivity.defn,
                arg=KeycloakClientSetupActivityModel(
                    tenant=tenant,
                    realm_name="dexithelp",
                    domain=dexit_config.domain_name,
                    template_path=TemplatePath,
                    template_name="dexithelp_instance_idp_flow.json",
                    template_payload={"idp_config": dexit_config.idp_config, "auth_url": config.keycloak.auth_url},
                    is_prod=True,
                ),
                retry_policy=DexitKeycloakCreateIDPFlowActivity.get_retry_policy(),
                start_to_close_timeout=DexitKeycloakCreateIDPFlowActivity.get_timeout(),
            )

            # keycloak tenant customer admin user setup
            await workflow.execute_activity(
                activity=KeycloakCreateTenantCustomerAdminUserActivity.defn,
                arg=KeycloakCreateTenantCustomerAdminUserActivityModel(
                    realm_name=realm_name,
                    client_name="dexit",
                    username=email,
                    email=email,
                    firstname=first_name,
                    lastname=last_name,
                    template_path=TemplatePath,
                    template_name="keycloak_user.json",
                ),
                retry_policy=KeycloakCreateTenantCustomerAdminUserActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakCreateTenantCustomerAdminUserActivity.get_timeout(),
            )

            # dns setup for api
            await run_activity(
                activity=CreateCloudflareDNSRecordActivity,
                arg=CreateCloudflareDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{dexit_config.domain_name}",
                    zone_id=dexit_config.zone_id,
                    content=config.k8s_cname,
                ),
            )

            # create bucket
            bucket_name = f"{tenant}-{dexit_config.domain_name.replace('.', '-')}"
            await run_activity(
                activity=CreateCloudflareBucketActivity,
                arg=CreateCloudflareBucketActivityModel(bucket_name=bucket_name),
            )

            # link bucket to custom domain
            await run_activity(
                activity=LinkBucketToDomainActivity,
                arg=LinkBucketToDomainActivityModel(
                    bucket_name=bucket_name,
                    domain_name=f"{tenant}.{dexit_config.domain_name}",
                    zone_id=dexit_config.zone_id,
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
                                ],
                            },
                            "exposeHeaders": ["ETag", "Location", "Content-Disposition"],
                        }
                    ],
                ),
            )

            # propagate the dns record
            await run_activity(
                activity=PropagateDNSRecordActivity,
                arg=PropagateDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{dexit_config.domain_name}",
                ),
            )

            # ui setup
            repo_name = "dexit-ui"
            image_tag = "production" if config.env == "production" else "sprint"

            if config.env == "production":
                dest_dir = f"{bucket_name}/"
            else:
                dest_dir = f"{bucket_name}/{image_tag}"

            src_object_name = f"{repo_name}/{image_tag}/bundle.zip"

            bundle_path = "bundle/dist/admin"

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

            # s3 bucket name added to onepassword
            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=tenant,
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
                    tenant=tenant,
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
                    tenant=tenant,
                    vault=OnePasswordVaultName,
                    server_item=server_item,
                    key="s3_secret_key",
                    key_value=credentials.secret_key,
                ),
            )

            tenant_config = "tenant-config.json"
            mlops_config = "mlops-config.json"
            env_config = "env-config.json"
            dicom_config = "dicom-config.json"
            vector_config = "vector-config.toml"
            config_dir = "config"

            # setup tenant configmap
            for config_map in [
                {
                    "name": "dexit-tenant-config",
                    "key": tenant_config,
                    "template_file_name": f"{config.env}-tenant-config.tmpl.json",
                },
                {
                    "name": "dexit-mlops-config",
                    "key": mlops_config,
                    "template_file_name": f"{config.env}-mlops-config.tmpl.json",
                },
                {
                    "name": "dexit-env-config",
                    "key": env_config,
                    "template_file_name": f"{config.env}-env-config.tmpl.json",
                },
                {
                    "name": "dexit-dicom-config",
                    "key": dicom_config,
                    "template_file_name": f"{config.env}-dicom-config.tmpl.json",
                },
                {
                    "name": "dexit-cli-vector-config",
                    "key": vector_config,
                    "template_file_name": f"{config.env}-vector-config.tmpl.toml",
                },
            ]:
                await run_activity(
                    activity=K8sConfigMapCreationActivity,
                    arg=K8sConfigMapCreationActivityModel(
                        namespace=tenant,
                        name=config_map["name"],
                        template_file_name=config_map["template_file_name"],
                        destination_file_name=config_map["key"],
                        bucket_name="dexit-config",
                        template_payload={"tenant": tenant},
                    ),
                )

            # atlas job
            await run_activity(
                activity=DatabaseMigrationJobActivity,
                arg=DatabaseMigrationJobActivityModel(
                    namespace=tenant,
                    job_name="dexit-atlas-migration-job",
                    docker_image=docker_image,
                    volume_mounts=[
                        {
                            "name": "dexit-env-config",
                            "mount_path": f"/{config_dir}/{env_config}",
                            "sub_path": env_config,
                        },
                        {
                            "name": "dexit-tenant-config",
                            "mount_path": f"/{config_dir}/{tenant_config}",
                            "sub_path": tenant_config,
                        },
                        {
                            "name": "dexit-mlops-config",
                            "mount_path": f"/{config_dir}/{mlops_config}",
                            "sub_path": mlops_config,
                        },
                    ],
                    volumes=[
                        {
                            "name": "dexit-env-config",
                            "config_map_name": "dexit-env-config",
                            "key": env_config,
                            "path": env_config,
                        },
                        {
                            "name": "dexit-tenant-config",
                            "config_map_name": "dexit-tenant-config",
                            "key": tenant_config,
                            "path": tenant_config,
                        },
                        {
                            "name": "dexit-mlops-config",
                            "config_map_name": "dexit-mlops-config",
                            "key": mlops_config,
                            "path": mlops_config,
                        },
                    ],
                    container_envs=[
                        {"name": "APP_CONFIG_DIR", "value": f"/{config_dir}"},
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "CLIENT_CODE", "value": tenant},
                        {"name": "POSTGRES_PASSWORD", "value": postgres_password},
                        {"name": "POSTGRES_USER", "value": postgres_username},
                    ],
                    argument="python3 /app/provisioning/atlas_migration.py",
                    job_type="atlas",
                    product=ProductName,
                ),
            )

            # kubernetes service
            await run_activity(
                activity=KubernetesServiceActivity,
                arg=KubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="dexit",
                    ports={"http": 8000},
                ),
            )

            template_env = get_env(template_path=TemplatePath)

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
                    host=f"{tenant}.api.{dexit_config.domain_name}",
                    service_name="dexit-vs",
                    payload=http_list,
                ),
            )

            # statefulset pod creation for server
            await run_activity(
                activity=KubernetesDeploymentActivity,
                arg=KubernetesDeploymentActivityModel(
                    namespace=tenant,
                    name="dexit",
                    docker_image=docker_image,
                    request_resource={
                        "cpu": pydash.get(dexit, "serverSpec.request_cpu"),
                        "memory": pydash.get(dexit, "serverSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(dexit, "serverSpec.limit_cpu"),
                        "memory": pydash.get(dexit, "serverSpec.limit_memory"),
                    },
                    container_ports={"http": 8000},
                    volume_mounts=[
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
                            "name": "mlops-volume",
                            "mount_path": f"/{config_dir}/{mlops_config}",
                            "sub_path": mlops_config,
                        },
                    ],
                    volumes=[
                        {
                            "name": "env-volume",
                            "config_map_name": "dexit-env-config",
                            "key": env_config,
                            "path": env_config,
                        },
                        {
                            "name": "tenant-volume",
                            "config_map_name": "dexit-tenant-config",
                            "key": tenant_config,
                            "path": tenant_config,
                        },
                        {
                            "name": "mlops-volume",
                            "config_map_name": "dexit-mlops-config",
                            "key": mlops_config,
                            "path": mlops_config,
                        },
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "WEB_CONCURRENCY", "value": "5"},
                        {"name": "CLIENT_CODE", "value": tenant},
                        {"name": "APP_CONFIG_DIR", "value": f"/{config_dir}"},
                        {"name": "POSTGRES_PASSWORD", "value": postgres_password},
                        {"name": "POSTGRES_USER", "value": postgres_username},
                        {"name": "RELEASE_VERSION", "value": image_tag},
                        {"name": "TIKA_SERVER_ENDPOINT", "value": dexit_config.tika_server_endpoint},
                        {"name": "CLI", "value": "FALSE"},
                    ],
                ),
            )

            # statefulset pod creation for cli
            cli_pods = {"dexit-worker-all" : "all_workers", "dexit-worker-dsl" : "dsl_processing_worker", "dexit-worker-dslp" : "dsl_processing_worker_priority", 
                               "dexit-worker-event" : "event_processing_worker"}
            
            for key, value in cli_pods.items():

                await run_activity(
                    activity=KubernetesDeploymentActivity,
                    arg=KubernetesDeploymentActivityModel(
                        namespace=tenant,
                        name=key,
                        docker_image=docker_image,
                        request_resource={
                            "cpu": pydash.get(dexit, "cliSpec.request_cpu"),
                            "memory": pydash.get(dexit, "cliSpec.request_memory"),
                        },
                        limit_resource={
                            "cpu": pydash.get(dexit, "cliSpec.limit_cpu"),
                            "memory": pydash.get(dexit, "cliSpec.limit_memory"),
                        },
                        container_ports={"http": 8000},
                        volume_mounts=[
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
                                "name": "mlops-volume",
                                "mount_path": f"/{config_dir}/{mlops_config}",
                                "sub_path": mlops_config,
                            },
                            {"name": "vector-volume", "mount_path": "/vector", "read_only": True},
                        ],
                        volumes=[
                            {
                                "name": "env-volume",
                                "config_map_name": "dexit-env-config",
                                "key": env_config,
                                "path": env_config,
                            },
                            {
                                "name": "tenant-volume",
                                "config_map_name": "dexit-tenant-config",
                                "key": tenant_config,
                                "path": tenant_config,
                            },
                            {
                                "name": "mlops-volume",
                                "config_map_name": "dexit-mlops-config",
                                "key": mlops_config,
                                "path": mlops_config,
                            },
                            {
                                "name": "vector-volume",
                                "config_map_name": "dexit-cli-vector-config",
                                "key": vector_config,
                                "path": vector_config,
                            },
                        ],
                        container_envs=[
                            {"name": "DEPLOYMENT", "value": config.env},
                            {"name": "CLIENT_CODE", "value": tenant},
                            {"name": "APP_CONFIG_DIR", "value": f"/{config_dir}"},
                            {"name": "POSTGRES_PASSWORD", "value": postgres_password},
                            {"name": "POSTGRES_USER", "value": postgres_username},
                            {"name": "RELEASE_VERSION", "value": image_tag},
                            {"name": "TIKA_SERVER_ENDPOINT", "value": dexit_config.tika_server_endpoint},
                            {"name": "CLI", "value": "TRUE"},
                            {"name": "WORKER_NAME", "value": value},
                        ],
                    ),
                )

            # statefulset pod creation for dicom
            await run_activity(
                activity=KubernetesDeploymentActivity,
                arg=KubernetesDeploymentActivityModel(
                    namespace=tenant,
                    name="dexit-dicom",
                    docker_image="orthancteam/orthanc:24.8.1",
                    request_resource={
                        "cpu": pydash.get(dexit, "serverSpec.request_cpu"),
                        "memory": pydash.get(dexit, "serverSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(dexit, "serverSpec.limit_cpu"),
                        "memory": pydash.get(dexit, "serverSpec.limit_memory"),
                    },
                    container_ports={},
                    volume_mounts=[
                        {
                            "name": "dicom-volume",
                            "mount_path": "/etc/orthanc/orthanc.json",
                            "sub_path": dicom_config,
                        },
                    ],
                    volumes=[
                        {
                            "name": "dicom-volume",
                            "config_map_name": "dexit-dicom-config",
                            "key": dicom_config,
                            "path": dicom_config,
                        },
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "WEB_CONCURRENCY", "value": "5"},
                        {"name": "CLIENT_CODE", "value": tenant},
                        {"name": "APP_CONFIG_DIR", "value": f"/{config_dir}"},
                        {"name": "RELEASE_VERSION", "value": image_tag},
                    ],
                ),
            )

            # kubernetes service for dicom
            await run_activity(
                activity=KubernetesServiceActivity,
                arg=KubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="dexit-dicom",
                    ports={"http": 8042},
                ),
            )

            # vm pod scraper
            await run_activity(
                activity=VMPodScrapperActivity,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="dexit-metrics",
                    app="dexit",
                    path="/metrics/",
                    interval="15s",
                ),
            )

            # temporal namespace creation
            await run_activity(
                activity=TemporalNamespaceActivity,
                arg=TemporalNamespaceActivityModel(
                    namespace=f"dexit_{tenant}",
                ),
            )

            # temporal search attributes creation
            await run_activity(
                activity=TemporalSearchAttributesCreationActivity,
                arg=TemporalSearchAttributesCreationActivityModel(
                    namespace=f"dexit_{tenant}",
                ),
            )

            # check pod running status
            for pod in ["dexit", "dexit-dicom"] + list(cli_pods.keys()):
                await run_activity(
                    activity=CheckPodRunningStatusActivity,
                    arg=CheckPodRunningStatusActivityModel(
                        namespace=tenant,
                        name=pod,
                    ),
                    retry_policy=CheckPodRunningStatusActivity.get_retry_policy(),
                    start_to_close_timeout=CheckPodRunningStatusActivity.get_timeout(),
                )

            # zsegment onboarding
            await run_activity(
                activity=ZSegmentSetupActivity,
                arg=ZSegmentSpec(tenant=tenant, email=email, firstName=first_name, lastName=last_name),
            )

        except Exception as e:
            workflow.logger.error(f"Error in onboarding workflow: {e}")
            raise e
