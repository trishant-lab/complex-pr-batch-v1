from collections.abc import Callable
from typing import TYPE_CHECKING

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

from app.cli.temporal.activities.k8s_config_map import (
    K8sConfigMapCreationActivity,
    K8sConfigMapCreationActivityModel,
)
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
    KeycloakClientSetupActivity,
    KeycloakClientSetupActivityModel,
    KeycloakCreateClientRolesActivity,
    KeycloakCreateClientRolesActivityModel,
    KeycloakCreateGroupActivity,
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
    OnePasswordGetActivity,
    OnePasswordGetActivityModel,
    OnePasswordInsertIfNotExistsActivity,
    OnePasswordInsertIfNotExistsActivityModel,
)
from app.cli.temporal.activities.postgres_setup import (
    KeycloakUserMappingActivity,
    KeycloakUserMappingActivityModel,
    MatomoUserMappingActivity,
    MatomoUserMappingActivityModel,
    PostgresGrantAccessToUserActivity,
    PostgresGrantAccessToUserActivityModel,
    PostgresGrantAllPrivilegesOnTableActivity,
    PostgresSchemaCreationActivity,
    PostgresSchemaCreationActivityModel,
    PostgresSupavisorPollUserActivity,
    PostgresSupavisorPollUserActivityModel,
    PostgresUserCreationActivity,
    PostgresUserCreationActivityModel,
)
from app.cli.temporal.activities.redis import (
    RedisSetupActivity,
    RedisSetupActivityModel,
)
from app.cli.temporal.activities.send_mail import (
    SendAfterProvisioningMailActivity,
    SendAfterProvisioningMailActivityModel,
    SendBeforeProvisioningMailActivity,
    SendBeforeProvisioningMailActivityModel,
)
from app.cli.temporal.activities.slack_notification_activity import (
    SlackNotificationActivity,
    SlackNotificationActivityModel,
)
from app.cli.temporal.activities.stateful_set_pod_creation import (
    CheckPodRunningStatusActivity,
    CheckPodRunningStatusActivityModel,
)
from app.cli.temporal.activities.temporal_namespace import (
    TemporalNamespaceActivity,
)
from app.cli.temporal.activities.update_tenant_status import (
    TenantCliStatus,
    UpdateTenantStatusActivity,
)
from app.cli.temporal.activities.vm_pod_scrapper import (
    VMPodScrapperActivity,
    VMPodScrapperActivityModel,
)
from app.cli.temporal.core.base import Workflow
from app.cli.temporal.pricedx import TemplatePath
from app.cli.temporal.pricedx.models.pricedx_spec import PricedxSpec
from app.cli.temporal.models.cloudflare import (
    CopyArtifactsToBucketActivityModel,
    CreateCloudflareBucketActivityModel,
    CreateCloudflareBucketCredentialsActivityModel,
    CreateCloudflareDNSRecordActivityModel,
    LinkBucketToDomainActivityModel,
    PropagateDNSRecordActivityModel,
    UpdateCORSForBucketActivityModel,
)
from app.common import generate_password
from app.core.ijson import ijson_loads
from app.core.settings import AppSettings, PricedxSettings, get_settings
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum
from app.template_env import get_env

if TYPE_CHECKING:
    from app.cli.temporal.models.cloudflare import CloudflareBucketCredentials

ProductName = "pricedx"
OnePasswordVaultName = "Pricedx"


@workflow.defn(name="PricedxOnboardingWorkflow", sandboxed=False)
class PricedxOnboardingWorkflow(Workflow):
    """
    Pricedx Onboarding Workflow
    """

    def __init__(self: "Workflow") -> None:
        self.approved: bool = False
        self.deny: bool = False

    @staticmethod
    def get_activities() -> list[type[Callable]]:  # type: ignore
        """
        Return list of activities used in the workflow
        """
        return [
            SendBeforeProvisioningMailActivity.defn,
            UpdateTenantStatusActivity.defn,
            PostgresUserCreationActivity.defn,
            PostgresSupavisorPollUserActivity.defn,
            PostgresSchemaCreationActivity.defn,
            PostgresGrantAccessToUserActivity.defn,
            KeycloakUserMappingActivity.defn,
            MatomoUserMappingActivity.defn,
            PostgresGrantAllPrivilegesOnTableActivity.defn,
            K8sNamespaceCreationActivity.defn,
            K8sSecretCreationActivity.defn,
            DatabaseMigrationJobActivity.defn,
            RedisSetupActivity.defn,
            KeycloakRealmSetupActivity.defn,
            KeycloakClientSetupActivity.defn,
            KeycloakCreateClientRolesActivity.defn,
            KeycloakCreateTenantCustomerAdminUserActivity.defn,
            KeycloakCreateInternalUsersActivity.defn,
            KubernetesDeploymentActivity.defn,
            VMPodScrapperActivity.defn,
            KubernetesIstioVirtualServiceActivity.defn,
            KubernetesServiceActivity.defn,
            K8sConfigMapCreationActivity.defn,
            TemporalNamespaceActivity.defn,
            CreateCloudflareDNSRecordActivity.defn,
            CreateCloudflareBucketActivity.defn,
            LinkBucketToDomainActivity.defn,
            CopyArtifactsToBucketActivity.defn,
            PropagateDNSRecordActivity.defn,
            OnePasswordCreateOrUpdateActivity.defn,
            OnePasswordGetActivity.defn,
            CheckPodRunningStatusActivity.defn,
            SlackNotificationActivity.defn,
            UpdateCORSForBucketActivity.defn,
            CreateCloudflareBucketCredentialsActivity.defn,
            OnePasswordInsertIfNotExistsActivity.defn,
            KeycloakCreateGroupActivity.defn,
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", pricedx: PricedxSpec) -> str:
        """
        Return workflow id
        """
        return f"pricedx_onboarding_workflow_{pydash.get(pricedx, 'tenant')}"

    @workflow.run
    async def run(self: "Workflow", pricedx: PricedxSpec) -> None:
        """
        Run the workflow
        """
        config: AppSettings = get_settings()
        pricedx_config: PricedxSettings = config.pricedx

        first_name = pydash.get(pricedx, "firstName")
        last_name = pydash.get(pricedx, "lastName")
        email = pydash.get(pricedx, "email")
        tenant = pydash.get(pricedx, "tenant")
        is_deployment = pydash.get(pricedx, "is_deployment")

        try:
            if not pydash.get(pricedx, "emailSent") and not is_deployment:
                await run_activity(
                    activity=SendBeforeProvisioningMailActivity,
                    arg=SendBeforeProvisioningMailActivityModel(
                        user_details={
                            "firstName": first_name,
                            "lastName": last_name,
                            "email": email,
                        },
                        product=ProductName,
                        from_name=pricedx_config.sender_name,
                        email_from=pricedx_config.sender_email,
                    ),
                )

            # Wait for approval or denial
            if not is_deployment:
                await workflow.wait_condition(lambda: self.approved or self.deny)

            # Update tenant status if request is declined
            if self.deny:
                await run_activity(
                    activity=UpdateTenantStatusActivity,
                    arg=TenantCliStatus(
                        tenant_name=tenant,
                        status=TenantStatusEnum.Declined,
                        error_msg="Request Declined",
                        product=ProductEnum.pricedx,
                    ),
                )
                return

            postgres_schema_name = tenant
            postgres_database_name = "pricedx"
            postgres_username = f"{ProductName}_{tenant}"
            postgres_password = generate_password(length=20)

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    secret_name="auth_secret",
                    secret_value=pricedx_config.auth_secret,
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
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    secret_name="pg_password",
                    secret_value=postgres_password,
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
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    secret_name="pg_dsn",
                    secret_value=pricedx_config.pg_dsn_template.format(tenant=tenant, password=postgres_password),
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
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    secret_name="db_schema_name",
                    secret_value=postgres_schema_name,
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


            # setup redis
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
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    secret_name="redis_password",
                    secret_value=redis_tenant_password,
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    secret_name="redis_dsn",
                    secret_value=pricedx_config.redis_dsn_template.format(tenant=tenant),
                ),
            )

            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    key="org_domains",
                    key_value="",
                ),
            )

            # dns setup for api
            await run_activity(
                activity=CreateCloudflareDNSRecordActivity,
                arg=CreateCloudflareDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{pricedx_config.domain_name}",
                    zone_id=pricedx_config.zone_id,
                    content=config.k8s_cname,
                ),
            )

            # create bucket
            bucket_name = f"{tenant}-{pricedx_config.domain_name.replace('.', '-')}"
            await run_activity(
                activity=CreateCloudflareBucketActivity,
                arg=CreateCloudflareBucketActivityModel(
                    bucket_name=bucket_name, location_hint=pricedx_config.location_hint
                ),
            )

            # link bucket to custom domain
            await run_activity(
                activity=LinkBucketToDomainActivity,
                arg=LinkBucketToDomainActivityModel(
                    bucket_name=bucket_name,
                    domain_name=f"{tenant}.{pricedx_config.domain_name}",
                    zone_id=pricedx_config.zone_id,
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
                            "exposeHeaders": ["ETag", "Location"],
                        }
                    ],
                ),
            )

            repo_name = "pricedx-ui"
            image_tag = server_image_tag = "sprint"
            dest_dir = f"{bucket_name}/{image_tag}"
            if config.env == "production":
                image_tag = "production"
                server_image_tag = "production"
                dest_dir = f"{bucket_name}/"

            docker_image = f"registry.314ecorp.tech/pricedx-app:{server_image_tag}"

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
                    server_item="application-config",
                    key="base_url_cdn",
                    key_value=f"https://{tenant}.{pricedx_config.domain_name}",
                ),
            )

            # s3 media bucket name added to onepassword
            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    key="s3_media_bucket_name",
                    key_value=bucket_name,
                ),
            )

            # s3 access key added to onepassword
            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item="application-config",
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
                    server_item="application-config",
                    key="s3_secret_key",
                    key_value=credentials.secret_key,
                ),
            )

            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    key="s3_ui_bucket_name",
                    key_value=bucket_name,
                ),
            )
            # s3 access key added to onepassword
            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    key="s3_ui_bucket_access_key",
                    key_value=credentials.access_key,
                ),
            )

            # s3 secret key added to onepassword
            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    key="s3_ui_bucket_secret_key",
                    key_value=credentials.secret_key,
                ),
            )

            # additional required onepassword configs
            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    key="base_ui_url",
                    key_value=pricedx_config.base_ui_url.format(tenant=tenant),
                ),
            )


            # setup configmaps
            tenant_config = "config.toml"
            config_dir = "config"

            # setup tenant configmap
            for config_map in [
                {
                    "name": "pricedx-tenant-config",
                    "key": tenant_config,
                    "template_file_name": f"{config.env}-config.tmpl.toml",
                },
            ]:
                await run_activity(
                    activity=K8sConfigMapCreationActivity,
                    arg=K8sConfigMapCreationActivityModel(
                        namespace=tenant,
                        name=config_map["name"],
                        template_file_name=config_map["template_file_name"],
                        destination_file_name=config_map["key"],
                        cloudflare_r2_folder_path="pricedx-config",
                        template_payload={"tenant": tenant},
                    ),
                )

            # keycloak realm setup
            realm_name = f"pricedx_{tenant}"

            await run_activity(
                activity=KeycloakRealmSetupActivity,
                arg=KeycloakRealmSetupActivityModel(
                    realm_name=realm_name,
                    domain=pricedx_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_realm.json",
                    template_payload={
                        "company_name": pydash.get(pricedx, "companyName"),
                        "smtp_password": pricedx_config.keycloak_smtp_password,
                    },
                ),
            )

            # keycloak client setup
            await run_activity(
                activity=KeycloakClientSetupActivity,
                arg=KeycloakClientSetupActivityModel(
                    tenant=tenant,
                    realm_name=realm_name,
                    domain=pricedx_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_pricedx_client.json",
                    template_payload={"chatwoot_domain": pricedx_config.chatwoot_domain},
                ),
            )

            roles = [
                "admin",
                "user",
                "super_admin",
            ]
            # keycloak client roles setup
            await run_activity(
                activity=KeycloakCreateClientRolesActivity,
                arg=KeycloakCreateClientRolesActivityModel(
                    client_name="pricedx",
                    realm_name=realm_name,
                    roles=roles,
                ),
            )




            # keycloak tenant customer admin user setup
            await run_activity(
                activity=KeycloakCreateTenantCustomerAdminUserActivity,
                arg=KeycloakCreateTenantCustomerAdminUserActivityModel(
                    realm_name=realm_name,
                    client_name=ProductName,
                    username=email,
                    email=email,
                    firstname=first_name,
                    lastname=last_name,
                    template_path=TemplatePath,
                    template_name="keycloak_tenant_admin.json",
                    roles=[role for role in roles],
                ),
            )

            # keycloak internal users setup
            await run_activity(
                activity=KeycloakCreateInternalUsersActivity,
                arg=KeycloakCreateInternalUsersActivityModel(
                    realm_name=realm_name,
                    client_name="pricedx",
                    template_path=TemplatePath,
                    template_name="keycloak_tenant_internal_user.json",
                    users=ijson_loads(open(f"{TemplatePath}/{config.env}_internal_users.json").read()),
                    roles=[role for role in roles],
                ),
            )

            # atlas job
            await run_activity(
                activity=DatabaseMigrationJobActivity,
                arg=DatabaseMigrationJobActivityModel(
                    namespace=tenant,
                    job_name="pricedx-db-schema-migration-job",
                    docker_image=docker_image,
                    volume_mounts=[
                        {
                            "name": "tenant-volume",
                            "mount_path": f"/{config_dir}/{tenant_config}",
                            "sub_path": tenant_config,
                        },
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "pricedx-tenant-config",
                            "key": tenant_config,
                            "path": tenant_config,
                        },
                    ],
                    container_envs=[
                        {"name": "APP_CONFIG_FILE", "value": f"/{config_dir}/{tenant_config}"},
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
                    service_name="pricedx",
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
                    host=f"{tenant}.api.{pricedx_config.domain_name}",
                    service_name="pricedx-vs",
                    payload=http_list,
                ),
            )

            dynamic_url_hash_key = await run_activity(
                activity=OnePasswordGetActivity,
                arg=OnePasswordGetActivityModel(
                    tenant="INTEGRATION_COMMON_CONFIG" if config.env != "production" else "PRODUCTION_COMMON_CONFIG",
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    secret_name="dynamic_url_hash_key",
                ),
            )

            # deployment pod creation for server
            await run_activity(
                activity=KubernetesDeploymentActivity,
                arg=KubernetesDeploymentActivityModel(
                    namespace=tenant,
                    name="pricedx",
                    docker_image=docker_image,
                    request_resource={
                        "cpu": pydash.get(pricedx, "serverSpec.request_cpu"),
                        "memory": pydash.get(pricedx, "serverSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(pricedx, "serverSpec.limit_cpu"),
                        "memory": pydash.get(pricedx, "serverSpec.limit_memory"),
                    },
                    container_ports={"http": 8000},
                    volume_mounts=[
                        {
                            "name": "tenant-volume",
                            "mount_path": f"/{config_dir}/{tenant_config}",
                            "sub_path": tenant_config,
                        },
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "pricedx-tenant-config",
                            "key": tenant_config,
                            "path": tenant_config,
                        },
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "WEB_CONCURRENCY", "value": "5"},
                        {"name": "CLIENT_CODE", "value": tenant},
                        {"name": "APP_CONFIG_FILE", "value": f"/{config_dir}/{tenant_config}"},
                        {"name": "POSTGRES_PASSWORD", "value": postgres_password},
                        {"name": "POSTGRES_USER", "value": postgres_username},
                        {"name": "EXTRACTOR_ENABLED", "value": "FALSE"},
                        {"name": "DYNAMIC_URL_HASH_KEY", "value": dynamic_url_hash_key},
                        {"name": "DYNAMIC_URL_ENABLED", "value": "True"},
                    ],
                ),
            )

            # deployment pod creation for cli
            await run_activity(
                activity=KubernetesDeploymentActivity,
                arg=KubernetesDeploymentActivityModel(
                    namespace=tenant,
                    name="pricedx-worker",
                    docker_image=docker_image,
                    request_resource={
                        "cpu": pydash.get(pricedx, "cliSpec.request_cpu"),
                        "memory": pydash.get(pricedx, "cliSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(pricedx, "cliSpec.limit_cpu"),
                        "memory": pydash.get(pricedx, "cliSpec.limit_memory"),
                    },
                    container_ports={"http": 8000},
                    volume_mounts=[
                        {
                            "name": "tenant-volume",
                            "mount_path": f"/{config_dir}/{tenant_config}",
                            "sub_path": tenant_config,
                        },
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "pricedx-tenant-config",
                            "key": tenant_config,
                            "path": tenant_config,
                        },
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "CLIENT_CODE", "value": tenant},
                        {"name": "APP_CONFIG_FILE", "value": f"/{config_dir}/{tenant_config}"},
                        {"name": "POSTGRES_PASSWORD", "value": postgres_password},
                        {"name": "POSTGRES_USER", "value": postgres_username},
                        {"name": "EXTRACTOR_ENABLED", "value": "TRUE"},
                        {"name": "DYNAMIC_URL_HASH_KEY", "value": dynamic_url_hash_key},
                        {"name": "DYNAMIC_URL_ENABLED", "value": "True"},
                    ],
                ),
            )

            # vm pod scraper
            await run_activity(
                activity=VMPodScrapperActivity,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="pricedx-metrics",
                    app="pricedx",
                    path="/metrics/",
                    interval="15s",
                ),
            )

            await run_activity(
                activity=VMPodScrapperActivity,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="pricedx-worker-metrics",
                    app="pricedx",
                    path="/metrics/",
                    interval="15s",
                ),
            )

            # propagate the dns record
            await run_activity(
                activity=PropagateDNSRecordActivity,
                arg=PropagateDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{pricedx_config.domain_name}",
                ),
            )

            # check pod running status
            for pod in ["pricedx", "pricedx-worker"]:
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
                    tenant_name=tenant, status=TenantStatusEnum.Provisioned, product=ProductEnum.pricedx
                ),
            )
            # Send after provisioning mail
            if not is_deployment:
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
                    domain_name=pricedx_config.domain_name,
                    product=ProductName,
                    from_name=pricedx_config.sender_name,
                    email_from=pricedx_config.sender_email,
                ),
            )

        except Exception as e:
            workflow.logger.error(f"Error in onboarding workflow: {e}")
            await run_activity(
                activity=UpdateTenantStatusActivity,
                arg=TenantCliStatus(
                    tenant_name=tenant,
                    status=TenantStatusEnum.Failed if not is_deployment else TenantStatusEnum.DeploymentFailed,
                    error_msg=str(e),
                    product=ProductEnum.pricedx,
                ),
            )
            await run_activity(
                activity=SlackNotificationActivity,
                arg=SlackNotificationActivityModel(
                    product=ProductName,
                    error_message=str(e),
                ),
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
