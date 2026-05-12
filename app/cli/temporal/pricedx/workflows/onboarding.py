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
    OnePasswordInsertIfNotExistsActivity,
    OnePasswordInsertIfNotExistsActivityModel,
)
from app.cli.temporal.activities.postgres_setup import (
    KeycloakUserMappingActivity,
    # KeycloakUserMappingActivityModel,
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
from app.cli.temporal.models.cloudflare import (
    CopyArtifactsToBucketActivityModel,
    CreateCloudflareBucketActivityModel,
    CreateCloudflareDNSRecordActivityModel,
    LinkBucketToDomainActivityModel,
    PropagateDNSRecordActivityModel,
    UpdateCORSForBucketActivityModel,
)
from app.cli.temporal.pricedx import TemplatePath
from app.cli.temporal.pricedx.models.pricedx_spec import PricedxSpec
from app.common import generate_password
from app.core.ijson import ijson_loads
from app.core.settings import AppSettings, PricedxSettings, get_settings
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum
from app.template_env import get_env

ProductName = "pricedx"
OnePasswordVaultName = "Pricedx"


@workflow.defn(name="PricedxOnboardingWorkflow", sandboxed=False)
class PricedxOnboardingWorkflow(Workflow):
    """
    Pricedx Onboarding Workflow
    """

    @staticmethod
    def get_activities() -> list[type[Callable]]:  # type: ignore
        """
        Return list of activities used in the workflow
        """
        return [
            SendBeforeProvisioningMailActivity.defn,
            SendAfterProvisioningMailActivity.defn,
            UpdateTenantStatusActivity.defn,
            PostgresUserCreationActivity.defn,
            PostgresSupavisorPollUserActivity.defn,
            PostgresSchemaCreationActivity.defn,
            PostgresGrantAccessToUserActivity.defn,
            KeycloakUserMappingActivity.defn,
            PostgresGrantAllPrivilegesOnTableActivity.defn,
            K8sNamespaceCreationActivity.defn,
            K8sSecretCreationActivity.defn,
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
        is_console = pydash.get(pricedx, "isConsole")

        try:
            if not pydash.get(pricedx, "emailSent"):
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

            postgres_schema_name = tenant
            postgres_database_name = "pricedx"
            postgres_username = f"{ProductName}_{tenant}"
            postgres_password = generate_password(length=20)

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
                    secret_value=pricedx_config.pg_dsn_template.format(
                        tenant=tenant, password=postgres_password, schema_name=postgres_schema_name
                    ),
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
                    secret_name="pg_schema_name",
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

            # await run_activity(
            #     activity=KeycloakUserMappingActivity,
            #     arg=KeycloakUserMappingActivityModel(
            #         username=postgres_username,
            #         database_name=postgres_database_name,
            #     ),
            # )

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

            # setup redis
            redis_tenant_password = f"{ProductName}_{tenant}-{generate_password(length=20)}"
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

            repo_name = "pricedx-console-ui" if is_console else "pricedx-ui"
            server_image_name = "pricedx-console-app" if is_console else "pricedx-app"
            image_tag = server_image_tag = "sprint"
            dest_dir = f"{bucket_name}/{image_tag}"
            if config.env == "production":
                image_tag = "production"
                server_image_tag = "production"
                dest_dir = f"{bucket_name}/"

            docker_image = f"registry.314ecorp.tech/{server_image_name}:{server_image_tag}"

            src_object_name = f"{repo_name}/{image_tag}/bundle.zip"

            bundle_path = "bundle/tenant-dist"

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

            # setup configmaps
            tenant_config = "config.toml"
            config_dir = "config"

            template_file_name = f"{config.env}_config.tmpl.toml"

            if is_console:
                template_file_name = f"{config.env}_console_config.tmpl.toml"

            # setup tenant config map
            config_map = {
                "name": "pricedx-tenant-config",
                "key": tenant_config,
                "template_file_name": template_file_name,
            }

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
            realm_name = tenant

            await run_activity(
                activity=KeycloakRealmSetupActivity,
                arg=KeycloakRealmSetupActivityModel(
                    realm_name=realm_name,
                    domain=pricedx_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_realm.json",
                    template_payload={
                        "company_name": tenant,
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
                    roles=roles,
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
                    users=[
                        {
                            "username": pricedx_config.sendgrid.support_mail,
                            "email": pricedx_config.sendgrid.support_mail,
                            "firstname": "Admin",
                            "lastname": "",
                        },
                    ],
                    roles=roles,
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

            template = template_env.get_template("istio_rules.json")
            output = template.render(tenant=tenant, image_tag=image_tag, env=config.env)

            http_list = ijson_loads(output)

            # Redirect to the sprint on integration
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

            # propagate the dns record
            await run_activity(
                activity=PropagateDNSRecordActivity,
                arg=PropagateDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{pricedx_config.domain_name}",
                ),
            )

            # check pod running status
            await run_activity(
                activity=CheckPodRunningStatusActivity,
                arg=CheckPodRunningStatusActivityModel(
                    namespace=tenant,
                    name="pricedx",
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
                    status=TenantStatusEnum.ProvisioningFailed,
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
