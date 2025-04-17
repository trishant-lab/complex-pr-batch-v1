from collections.abc import Callable
from typing import TYPE_CHECKING

import pydash
from temporalio import workflow

from app.cli.activity_util import run_activity
from app.cli.temporal.activities.ai_voice_setup import (
    AiVoiceSetupActivity,
    AiVoiceSetupActivityModel,
)
from app.cli.temporal.activities.chatwoot_setup import (
    ChatwootSetupActivity,
    ChatwootSetupActivityModel,
)
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
from app.cli.temporal.activities.jeeves_fetch_latest_tag import (
    JeevesFetchLatestTagActivity,
)
from app.cli.temporal.activities.jeeves_novu_setup import JeevesNovuSetupActivity
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
    JeevesKeycloakCreateIDPFlowActivity,
    KeycloakClientSetupActivity,
    KeycloakClientSetupActivityModel,
    KeycloakCreateClientRolesActivity,
    KeycloakCreateClientRolesActivityModel,
    KeycloakCreateGroupActivity,
    KeycloakCreateGroupActivityModel,
    KeycloakCreateInternalUsersActivity,
    KeycloakCreateInternalUsersActivityModel,
    KeycloakCreateTenantCustomerAdminUserActivity,
    KeycloakCreateTenantCustomerAdminUserActivityModel,
    KeycloakRealmSetupActivity,
    KeycloakRealmSetupActivityModel,
    get_ehr_based_idp_template,
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
    PostgresGrantAllPrivilegesOnTableActivityModel,
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
    JeevesSendAfterProvisioningMailActivity,
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
    TemporalNamespaceActivityModel,
)
from app.cli.temporal.activities.update_tenant_status import (
    TenantCliStatus,
    UpdateTenantStatusActivity,
)
from app.cli.temporal.activities.vespa_job import VespaJobActivity
from app.cli.temporal.activities.vm_pod_scrapper import (
    VMPodScrapperActivity,
    VMPodScrapperActivityModel,
)
from app.cli.temporal.core.base import Workflow
from app.cli.temporal.jeeves import TemplatePath
from app.cli.temporal.jeeves.models.jeeves_spec import JeevesSpec
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
from app.core.settings import AppSettings, JeevesSettings, get_settings
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum
from app.template_env import get_env

if TYPE_CHECKING:
    from app.cli.temporal.models.cloudflare import CloudflareBucketCredentials

ProductName = "jeeves"
OnePasswordVaultName = "Jeeves"


@workflow.defn(name="JeevesOnboardingWorkflow", sandboxed=False)
class JeevesOnboardingWorkflow(Workflow):
    """
    Jeeves Onboarding Workflow
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
            ChatwootSetupActivity.defn,
            DatabaseMigrationJobActivity.defn,
            JeevesNovuSetupActivity.defn,
            RedisSetupActivity.defn,
            KeycloakRealmSetupActivity.defn,
            KeycloakClientSetupActivity.defn,
            KeycloakCreateClientRolesActivity.defn,
            KeycloakCreateTenantCustomerAdminUserActivity.defn,
            KeycloakCreateInternalUsersActivity.defn,
            VespaJobActivity.defn,
            AiVoiceSetupActivity.defn,
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
            JeevesKeycloakCreateIDPFlowActivity.defn,
            JeevesSendAfterProvisioningMailActivity.defn,
            UpdateCORSForBucketActivity.defn,
            CreateCloudflareBucketCredentialsActivity.defn,
            OnePasswordInsertIfNotExistsActivity.defn,
            JeevesFetchLatestTagActivity.defn,
            KeycloakCreateGroupActivity.defn,
            JeevesFetchLatestTagActivity.defn,
            KeycloakCreateGroupActivity.defn,
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", jeeves: JeevesSpec) -> str:
        """
        Return workflow id
        """
        return f"jeeves_onboarding_workflow_{pydash.get(jeeves, 'tenant')}"

    @workflow.run
    async def run(self: "Workflow", jeeves: JeevesSpec) -> None:
        """
        Run the workflow
        """
        config: AppSettings = get_settings()
        jeeves_config: JeevesSettings = config.jeeves

        first_name = pydash.get(jeeves, "firstName")
        last_name = pydash.get(jeeves, "lastName")
        email = pydash.get(jeeves, "email")
        tenant = pydash.get(jeeves, "tenant")
        is_deployment = pydash.get(jeeves, "is_deployment")
        ehr_used = pydash.get(jeeves, "whichEhrDoesYourCompanyUse")
        ehr_used = pydash.get(jeeves, "whichEhrDoesYourCompanyUse")

        try:
            if not pydash.get(jeeves, "emailSent") and not is_deployment:
                await run_activity(
                    activity=SendBeforeProvisioningMailActivity,
                    arg=SendBeforeProvisioningMailActivityModel(
                        user_details={
                            "firstName": first_name,
                            "lastName": last_name,
                            "email": email,
                        },
                        product=ProductName,
                        from_name=jeeves_config.sender_name,
                        email_from=jeeves_config.sender_email,
                    ),
                )

            # Wait for approval or denial
            if not is_deployment:
                await workflow.wait_condition(lambda: self.approved or self.denied)

            # Update tenant status if request is declined
            if self.denied:
                await run_activity(
                    activity=UpdateTenantStatusActivity,
                    arg=TenantCliStatus(
                        tenant_name=tenant,
                        status=TenantStatusEnum.ApprovalDeclined,
                        error_msg="Request Declined",
                        product=ProductEnum.jeeves,
                    ),
                )
                return

            postgres_schema_name = tenant
            postgres_database_name = "jeeves"
            postgres_username = f"{ProductName}_{tenant}"
            postgres_password = generate_password(length=20)

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    secret_name="auth_secret",
                    secret_value=jeeves_config.auth_secret,
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    secret_name="keycloak_attribute_to_match_user",
                    secret_value=jeeves_config.keycloak_attribute_to_match_user,
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    secret_name="ehr_field_to_match_user",
                    secret_value=jeeves_config.ehr_field_to_match_user,
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
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    secret_name="atlas_pg_dsn",
                    secret_value=jeeves_config.atlas_pg_dsn_template.format(tenant=tenant, password=postgres_password),
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
                    secret_value=jeeves_config.pg_dsn_template.format(tenant=tenant, password=postgres_password),
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
                        "keycloak_group",
                        "user_role_mapping",
                        "matomo_log_visit",
                        "matomo_log_action",
                        "matomo_log_media",
                        "matomo_log_link_visit_action",
                        "matomo_log_visit_view",
                        "matomo_log_action_view",
                        "matomo_log_media_view",
                        "matomo_log_link_visit_action_view",
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

            # setup chatwoot
            await run_activity(
                activity=ChatwootSetupActivity,
                arg=ChatwootSetupActivityModel(
                    tenant=tenant,
                    product=ProductName,
                    config=jeeves_config,
                ),
            )

            # setup novu
            await run_activity(
                activity=JeevesNovuSetupActivity,
                arg=jeeves,
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
                    secret_value=jeeves_config.redis_dsn_template.format(tenant=tenant),
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
                    domain_name=f"{tenant}.api.{jeeves_config.domain_name}",
                    zone_id=jeeves_config.zone_id,
                    content=config.k8s_cname,
                ),
            )

            # create bucket
            bucket_name = f"{tenant}-{jeeves_config.domain_name.replace('.', '-')}"
            await run_activity(
                activity=CreateCloudflareBucketActivity,
                arg=CreateCloudflareBucketActivityModel(
                    bucket_name=bucket_name, location_hint=jeeves_config.location_hint
                ),
            )

            # link bucket to custom domain
            await run_activity(
                activity=LinkBucketToDomainActivity,
                arg=LinkBucketToDomainActivityModel(
                    bucket_name=bucket_name,
                    domain_name=f"{tenant}.{jeeves_config.domain_name}",
                    zone_id=jeeves_config.zone_id,
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

            repo_name = "jeeves-ui"
            image_tag = server_image_tag = "sprint"
            dest_dir = f"{bucket_name}/{image_tag}"
            image_tag = server_image_tag = "sprint"
            dest_dir = f"{bucket_name}/{image_tag}"
            if config.env == "production":
                image_tag = "production"
                server_image_tag = await workflow.execute_activity(
                    activity=JeevesFetchLatestTagActivity.defn,
                    retry_policy=JeevesFetchLatestTagActivity.get_retry_policy(),
                    start_to_close_timeout=JeevesFetchLatestTagActivity.get_timeout(),
                )
                image_tag = "production"
                server_image_tag = await workflow.execute_activity(
                    activity=JeevesFetchLatestTagActivity.defn,
                    retry_policy=JeevesFetchLatestTagActivity.get_retry_policy(),
                    start_to_close_timeout=JeevesFetchLatestTagActivity.get_timeout(),
                )
                dest_dir = f"{bucket_name}/"

            docker_image = f"registry.314ecorp.tech/jeeves-app:{server_image_tag}"
            docker_image = f"registry.314ecorp.tech/jeeves-app:{server_image_tag}"

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
                    key_value=f"https://{tenant}.{jeeves_config.domain_name}",
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
                    key_value=jeeves_config.base_ui_url.format(tenant=tenant),
                ),
            )

            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    key="mpd_api",
                    key_value=jeeves_config.mpd_api.format(tenant=tenant),
                ),
            )

            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    key="s3_mpd_api",
                    key_value=jeeves_config.s3_mpd_api.format(tenant=tenant),
                ),
            )

            # setup configmaps
            tenant_config = "tenant-config.json"
            rclone_config = "rclone.conf"
            config_dir = "config"

            # setup tenant configmap
            for config_map in [
                {
                    "name": "jeeves-tenant-config",
                    "key": tenant_config,
                    "template_file_name": f"{config.env}-tenant-config.tmpl.json",
                },
                {
                    "name": "jeeves-rclone-config",
                    "key": rclone_config,
                    "template_file_name": f"{config.env}-rclone.tmpl.conf",
                },
            ]:
                await run_activity(
                    activity=K8sConfigMapCreationActivity,
                    arg=K8sConfigMapCreationActivityModel(
                        namespace=tenant,
                        name=config_map["name"],
                        template_file_name=config_map["template_file_name"],
                        destination_file_name=config_map["key"],
                        cloudflare_r2_folder_path="jeeves-config",
                        template_payload={"tenant": tenant},
                    ),
                )

            realm_name = tenant
            # keycloak realm setup
            await run_activity(
                activity=KeycloakRealmSetupActivity,
                arg=KeycloakRealmSetupActivityModel(
                    realm_name=realm_name,
                    domain=jeeves_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_realm.json",
                    template_payload={
                        "company_name": pydash.get(jeeves, "companyNameProvidersOrPayersOnly"),
                        "chatwoot_domain": jeeves_config.chatwoot_domain,
                        "smtp_password": jeeves_config.keycloak_smtp_password,
                    },
                ),
            )

            # keycloak client setup
            await run_activity(
                activity=KeycloakClientSetupActivity,
                arg=KeycloakClientSetupActivityModel(
                    tenant=tenant,
                    realm_name=realm_name,
                    domain=jeeves_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_jeeves_client.json",
                    template_payload={"chatwoot_domain": jeeves_config.chatwoot_domain},
                ),
            )

            roles = [
                "_allow-standalone-launch",
                "_access-reports",
                "_access-reports",
                "_can-manage-activities",
                "_allow-view-assets",
                "_allow-view-all-courses",
                "_access-manage-todos",
                "_access-users",
                "_can-manage-groups",
                "_allow-add-edit-assets",
                "_allow-view-assets",
                "_allow-view-all-courses",
                "_access-manage-todos",
                "_access-users",
                "_can-manage-groups",
                "_allow-add-edit-assets",
                "_allow-add-edit-courses",
                "_allow-publish-assets",
                "_allow-delete-assets",
                "_allow-publish-assets",
                "_allow-delete-assets",
                "_allow-delete-courses",
                "_can-manage-users",
                "_access-settings",
                "_developer",
                "_JEEVESALL",
                "_can-manage-users",
                "_access-settings",
                "_developer",
                "_JEEVESALL",
            ]
            # keycloak client roles setup
            await run_activity(
                activity=KeycloakCreateClientRolesActivity,
                arg=KeycloakCreateClientRolesActivityModel(
                    client_name="jeeves",
                    realm_name=realm_name,
                    roles=roles,
                ),
            )

            # keycloak user group setup
            await run_activity(
                activity=KeycloakCreateGroupActivity,
                arg=KeycloakCreateGroupActivityModel(
                    realm_name=realm_name,
                    client_name="jeeves",
                    template_path=TemplatePath,
                    template_name="keycloak_user_group.json",
                ),
            )

            # Create IDP mappers
            await run_activity(
                activity=JeevesKeycloakCreateIDPFlowActivity,
                arg=KeycloakClientSetupActivityModel(
                    tenant=tenant,
                    realm_name=realm_name,
                    domain=jeeves_config.domain_name,
                    template_path=TemplatePath,
                    template_name=get_ehr_based_idp_template(ehr=ehr_used),
                    template_payload={"idp_config": jeeves_config.idp_config},
                ),
            )

            await run_activity(
                activity=JeevesKeycloakCreateIDPFlowActivity,
                arg=KeycloakClientSetupActivityModel(
                    tenant=tenant,
                    realm_name="help",
                    domain=jeeves_config.domain_name,
                    template_path=TemplatePath,
                    template_name="help_instance_idp_flow.json",
                    template_payload={"idp_config": jeeves_config.idp_config, "auth_url": config.keycloak.auth_url},
                    is_prod=True,
                ),
            )

            # keycloak tenant customer admin user setup
            await run_activity(
                activity=KeycloakCreateTenantCustomerAdminUserActivity,
                arg=KeycloakCreateTenantCustomerAdminUserActivityModel(
                    realm_name=realm_name,
                    client_name="jeeves",
                    username=email,
                    email=email,
                    firstname=first_name,
                    lastname=last_name,
                    template_path=TemplatePath,
                    template_name="keycloak_tenant_customer_admin.json",
                    roles=[role for role in roles if role not in ["_JEEVESALL", "_developer"]],
                    group_path="Admin",
                ),
            )

            # keycloak internal users setup
            await run_activity(
                activity=KeycloakCreateInternalUsersActivity,
                arg=KeycloakCreateInternalUsersActivityModel(
                    realm_name=realm_name,
                    client_name="jeeves",
                    template_path=TemplatePath,
                    template_name="keycloak_tenant_internal_user.json",
                    users=ijson_loads(open(f"{TemplatePath}/{config.env}_internal_users.json").read()),
                    roles=[role for role in roles if role not in ["_JEEVESALL", "_developer"]],
                    group_path="Admin",
                ),
            )

            # atlas job
            await run_activity(
                activity=DatabaseMigrationJobActivity,
                arg=DatabaseMigrationJobActivityModel(
                    namespace=tenant,
                    job_name="jeeves-db-schema-migration-job",
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
                            "config_map_name": "jeeves-tenant-config",
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

            # vespa job
            await run_activity(
                activity=VespaJobActivity,
                arg=jeeves,
            )

            # kubernetes service
            await run_activity(
                activity=KubernetesServiceActivity,
                arg=KubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="jeeves",
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
                    host=f"{tenant}.api.{jeeves_config.domain_name}",
                    service_name="jeeves-vs",
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
                    name="jeeves",
                    docker_image=docker_image,
                    request_resource={
                        "cpu": pydash.get(jeeves, "serverSpec.request_cpu"),
                        "memory": pydash.get(jeeves, "serverSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(jeeves, "serverSpec.limit_cpu"),
                        "memory": pydash.get(jeeves, "serverSpec.limit_memory"),
                    },
                    container_ports={"http": 8000},
                    volume_mounts=[
                        {
                            "name": "tenant-volume",
                            "mount_path": f"/{config_dir}/{tenant_config}",
                            "sub_path": tenant_config,
                        },
                        {"name": "rclone-volume", "mount_path": "/root/.config/rclone/", "read_only": True},
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "jeeves-tenant-config",
                            "key": tenant_config,
                            "path": tenant_config,
                        },
                        {
                            "name": "rclone-volume",
                            "config_map_name": "jeeves-rclone-config",
                            "key": rclone_config,
                            "path": rclone_config,
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
                        {"name": "TIKA_SERVER_ENDPOINT", "value": jeeves_config.tika_server_endpoint},
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
                    name="jeeves-worker",
                    docker_image=docker_image,
                    request_resource={
                        "cpu": pydash.get(jeeves, "cliSpec.request_cpu"),
                        "memory": pydash.get(jeeves, "cliSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(jeeves, "cliSpec.limit_cpu"),
                        "memory": pydash.get(jeeves, "cliSpec.limit_memory"),
                    },
                    container_ports={"http": 8000},
                    volume_mounts=[
                        {
                            "name": "tenant-volume",
                            "mount_path": f"/{config_dir}/{tenant_config}",
                            "sub_path": tenant_config,
                        },
                        {"name": "rclone-volume", "mount_path": "/root/.config/rclone/", "read_only": True},
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "jeeves-tenant-config",
                            "key": tenant_config,
                            "path": tenant_config,
                        },
                        {
                            "name": "rclone-volume",
                            "config_map_name": "jeeves-rclone-config",
                            "key": rclone_config,
                            "path": rclone_config,
                        },
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "CLIENT_CODE", "value": tenant},
                        {"name": "APP_CONFIG_FILE", "value": f"/{config_dir}/{tenant_config}"},
                        {"name": "POSTGRES_PASSWORD", "value": postgres_password},
                        {"name": "POSTGRES_USER", "value": postgres_username},
                        {"name": "EXTRACTOR_ENABLED", "value": "TRUE"},
                        {"name": "TIKA_SERVER_ENDPOINT", "value": jeeves_config.tika_server_endpoint},
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
                    name="jeeves-metrics",
                    app="jeeves",
                    path="/metrics/",
                    interval="15s",
                ),
            )

            await run_activity(
                activity=VMPodScrapperActivity,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="jeeves-worker-metrics",
                    app="jeeves-worker",
                    path="/metrics/",
                    interval="15s",
                ),
            )

            # temporal namespace creation
            await run_activity(
                activity=TemporalNamespaceActivity,
                arg=TemporalNamespaceActivityModel(
                    namespace=f"jeeves_{tenant}",
                ),
            )

            # ai voice setup
            await run_activity(
                activity=AiVoiceSetupActivity,
                arg=AiVoiceSetupActivityModel(
                    tenant=tenant,
                    config=jeeves_config,
                ),
            )

            # propagate the dns record
            await run_activity(
                activity=PropagateDNSRecordActivity,
                arg=PropagateDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{jeeves_config.domain_name}",
                ),
            )

            # check pod running status
            for pod in ["jeeves", "jeeves-worker"]:
                await run_activity(
                    activity=CheckPodRunningStatusActivity,
                    arg=CheckPodRunningStatusActivityModel(
                        namespace=tenant,
                        name=pod,
                    ),
                )

            if not is_deployment:
                # update tenant status
                await run_activity(
                    activity=UpdateTenantStatusActivity,
                    arg=TenantCliStatus(
                        tenant_name=tenant,
                        status=TenantStatusEnum.Provisioned,
                        product=ProductEnum.jeeves,
                    ),
                )

        except Exception as e:
            workflow.logger.error(f"Error in onboarding workflow: {e}")
            if not is_deployment:
                await run_activity(
                    activity=UpdateTenantStatusActivity,
                    arg=TenantCliStatus(
                        tenant_name=tenant,
                        status=TenantStatusEnum.ProvisioningFailed,
                        error_msg=str(e),
                        product=ProductEnum.jeeves,
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
    async def decline(self: "Workflow") -> None:
        """
        Signal to reject the workflow
        """
        self.denied = True
