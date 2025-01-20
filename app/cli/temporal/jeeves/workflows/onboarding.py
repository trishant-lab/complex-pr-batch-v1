from collections.abc import Callable
import orjson
from temporalio import workflow
import pydash

from app.cli.temporal.activities.cloudflareSetup import (
    CopyArtifactsToBucketActivity,
    CopyArtifactsToBucketActivityModel,
    CreateCloudflareBucketActivity,
    CreateCloudflareBucketActivityModel,
    CreateCloudflareDNSRecordActivity,
    CreateCloudflareDNSRecordActivityModel,
    LinkBucketToDomainActivity,
    LinkBucketToDomainActivityModel,
    PropagateDNSRecordActivity,
    PropagateDNSRecordActivityModel,
)
from app.cli.temporal.activities.deployment import DeploymentDeletionActivity, DeploymentDeletionActivityModel
from app.cli.temporal.activities.slackNotificationActivity import (
    SlackNotificationActivity,
    SlackNotificationActivityModel,
)
from app.cli.temporal.activities.vespaJob import VespaJobActivity
from app.cli.temporal.activities.aiVoiceSetup import AiVoiceSetupActivity, AiVoiceSetupActivityModel
from app.cli.temporal.activities.chatwootSetup import ChatwootSetupActivity, ChatwootSetupActivityModel
from app.cli.temporal.activities.databaseMigrationJob import (
    DatabaseMigrationJobActivity,
    DatabaseMigrationJobActivityModel,
)
from app.cli.temporal.activities.onePassword import (
    OnePasswordCreateOrUpdateActivity,
    OnePasswordCreateOrUpdateActivityModel,
    OnePasswordGetActivity,
    OnePasswordGetActivityModel,
)
from app.cli.temporal.activities.jeevesNovuSetup import JeevesNovuSetupActivity
from app.cli.temporal.activities.k8sIstioVirtualService import (
    KubernetesIstioVirtualServiceActivity,
    KubernetesIstioVirtualServiceActivityModel,
)
from app.cli.temporal.activities.k8sSecret import K8sSecretCreationActivity, K8sSecretCreationActivityModel
from app.cli.temporal.activities.k8sService import KubernetesServiceActivity, KubernetesServiceActivityModel
from app.cli.temporal.activities.k8sconfigMap import K8sConfigMapCreationActivity, K8sConfigMapCreationActivityModel
from app.cli.temporal.activities.keycloakSetup import (
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
from app.cli.temporal.activities.preLoadAssetsJob import PreloadAssetsJobActivity
from app.cli.temporal.activities.redis import RedisSetupActivity, RedisSetupActivityModel
from app.cli.temporal.activities.sendMail import (
    SendAfterProvisioningMailActivity,
    SendAfterProvisioningMailActivityModel,
    SendBeforeProvisioningMailActivity,
    SendBeforeProvisioningMailActivityModel,
)
from app.cli.temporal.activities.statefulSetPodCreation import (
    CheckPodRunningStatusActivity,
    CheckPodRunningStatusActivityModel,
    KubernetesStatefulSetActivity,
    KubernetesStatefulSetActivityModel,
)
from app.cli.temporal.activities.temporalNamespace import TemporalNamespaceActivity, TemporalNamespaceActivityModel
from app.cli.temporal.activities.updateTenantStatus import TenantStatus, UpdateTenantStatusActivity
from app.cli.temporal.activities.vmPodScrapper import VMPodScrapperActivity, VMPodScrapperActivityModel
from app.cli.temporal.core.base import Workflow

from app.cli.temporal.activities.postgresSetup import (
    KeycloakUserMappingActivity,
    KeycloakUserMappingActivityModel,
    MatomoUserMappingActivity,
    MatomoUserMappingActivityModel,
    PostgresSchemaCreationActivityModel,
    PostgresSchemaCreationActivity,
    PostgresUserCreationActivity,
    PostgresGrantAccessToUserActivityModel,
    PostgresGrantAccessToUserActivity,
    PostgresGrantAllPrivilegesOnTableActivityModel,
    PostgresGrantAllPrivilegesOnTableActivity,
    PostgresUserCreationActivityModel,
    PostgresSupavisorPollUserActivity,
    PostgresSupavisorPollUserActivityModel,
)

from app.cli.temporal.activities.k8snamespace import K8sNamespaceCreationActivity, K8sNamespaceCreationActivityModel
from app.cli.temporal.jeeves import TemplatePath
from app.cli.temporal.jeeves.models.jeevesSpec import JeevesSpec


from app.common import generate_password
from app.core.settings import AppSettings, JeevesSettings, get_settings
from app.template_env import get_env


ProductName = "jeeves"
OnePasswordVaultName = "Jeeves"


@workflow.defn(name="JeevesOnboardingWorkflow", sandboxed=False)
class JeevesOnboardingWorkflow(Workflow):
    """
    Jeeves Onboarding Workflow
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
            SendAfterProvisioningMailActivity.defn,
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
            PreloadAssetsJobActivity.defn,
            VespaJobActivity.defn,
            AiVoiceSetupActivity.defn,
            KubernetesStatefulSetActivity.defn,
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
            DeploymentDeletionActivity.defn,
            CheckPodRunningStatusActivity.defn,
            SlackNotificationActivity.defn,
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

        try:
            if not pydash.get(jeeves, "emailSent") and not is_deployment:
                await workflow.execute_activity(
                    activity=SendBeforeProvisioningMailActivity.defn,
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
                    retry_policy=SendBeforeProvisioningMailActivity.get_retry_policy(),
                    start_to_close_timeout=SendBeforeProvisioningMailActivity.get_timeout(),
                )

            # Wait for approval or denial
            if not is_deployment:
                await workflow.wait_condition(lambda: self.approved or self.deny)

            # Update tenant status if request is declined
            if self.deny:
                await workflow.execute_activity(
                    activity=UpdateTenantStatusActivity.defn,
                    arg=TenantStatus(
                        tenant_name=tenant,
                        status="Declined",
                        error_msg="Request Declined",
                        product=ProductName,
                    ),
                    start_to_close_timeout=UpdateTenantStatusActivity.get_timeout(),
                    retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
                )
                return

            postgres_schema_name = tenant
            postgres_database_name = "jeeves"
            postgres_username = f"{ProductName}_{tenant}"
            postgres_password = generate_password(length=20)

            await workflow.execute_activity(
                activity=PostgresUserCreationActivity.defn,
                arg=PostgresUserCreationActivityModel(
                    username=postgres_username,
                    database_name=postgres_database_name,
                    password=postgres_password,
                ),
                retry_policy=PostgresUserCreationActivity.get_retry_policy(),
                start_to_close_timeout=PostgresUserCreationActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=OnePasswordCreateOrUpdateActivity.defn,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    secret_name="pg_password",
                    secret_value=postgres_password,
                ),
                retry_policy=OnePasswordCreateOrUpdateActivity.get_retry_policy(),
                start_to_close_timeout=OnePasswordCreateOrUpdateActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=PostgresSupavisorPollUserActivity.defn,
                arg=PostgresSupavisorPollUserActivityModel(
                    username=postgres_username,
                    database_name=postgres_database_name,
                    db_password=postgres_password,
                    template_path=TemplatePath,
                ),
                retry_policy=PostgresSupavisorPollUserActivity.get_retry_policy(),
                start_to_close_timeout=PostgresSupavisorPollUserActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=PostgresSchemaCreationActivity.defn,
                arg=PostgresSchemaCreationActivityModel(
                    schema_name=postgres_schema_name,
                    username=postgres_username,
                    database_name=postgres_database_name,
                ),
                retry_policy=PostgresSchemaCreationActivity.get_retry_policy(),
                start_to_close_timeout=PostgresSchemaCreationActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=PostgresGrantAccessToUserActivity.defn,
                arg=PostgresGrantAccessToUserActivityModel(
                    schema_name=postgres_schema_name,
                    username=postgres_username,
                    database_name=postgres_database_name,
                ),
                retry_policy=PostgresGrantAccessToUserActivity.get_retry_policy(),
                start_to_close_timeout=PostgresGrantAccessToUserActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=KeycloakUserMappingActivity.defn,
                arg=KeycloakUserMappingActivityModel(
                    username=postgres_username,
                    database_name=postgres_database_name,
                ),
                retry_policy=KeycloakUserMappingActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakUserMappingActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=MatomoUserMappingActivity.defn,
                arg=MatomoUserMappingActivityModel(
                    username=postgres_username,
                    database_name=postgres_database_name,
                ),
                retry_policy=MatomoUserMappingActivity.get_retry_policy(),
                start_to_close_timeout=MatomoUserMappingActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=PostgresGrantAllPrivilegesOnTableActivity.defn,
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
                        "matomo_log_visit_view",
                        "matomo_log_action_view",
                        "matomo_log_media_view",
                        "matomo_log_link_visit_action_view",
                    ],
                ),
                retry_policy=PostgresGrantAllPrivilegesOnTableActivity.get_retry_policy(),
                start_to_close_timeout=PostgresGrantAllPrivilegesOnTableActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=K8sNamespaceCreationActivity.defn,
                arg=K8sNamespaceCreationActivityModel(
                    namespace=tenant,
                ),
                retry_policy=K8sNamespaceCreationActivity.get_retry_policy(),
                start_to_close_timeout=K8sNamespaceCreationActivity.get_timeout(),
            )

            # secret setup for docker registry
            await workflow.execute_activity(
                activity=K8sSecretCreationActivity.defn,
                arg=K8sSecretCreationActivityModel(
                    namespace=tenant,
                    name="registrycred",
                    type="kubernetes.io/dockerconfigjson",
                    data={
                        ".dockerconfigjson": config.docker_image_pull_secret,
                    },
                ),
                retry_policy=K8sSecretCreationActivity.get_retry_policy(),
                start_to_close_timeout=K8sSecretCreationActivity.get_timeout(),
            )

            # secret setup for redis password
            await workflow.execute_activity(
                activity=K8sSecretCreationActivity.defn,
                arg=K8sSecretCreationActivityModel(
                    namespace=tenant,
                    name="cache-secret",
                    string_data={"REDIS_PASSWORD": config.cache_admin_password},
                ),
                retry_policy=K8sSecretCreationActivity.get_retry_policy(),
                start_to_close_timeout=K8sSecretCreationActivity.get_timeout(),
            )

            # setup chatwoot
            await workflow.execute_activity(
                activity=ChatwootSetupActivity.defn,
                arg=ChatwootSetupActivityModel(
                    tenant=tenant,
                    product=ProductName,
                    config=jeeves_config,
                ),
                retry_policy=ChatwootSetupActivity.get_retry_policy(),
                start_to_close_timeout=ChatwootSetupActivity.get_timeout(),
            )

            # setup novu
            await workflow.execute_activity(
                activity=JeevesNovuSetupActivity.defn,
                arg=jeeves,
                retry_policy=JeevesNovuSetupActivity.get_retry_policy(),
                start_to_close_timeout=JeevesNovuSetupActivity.get_timeout(),
            )

            # setup redis
            redis_tenant_password = generate_password(length=20)
            await workflow.execute_activity(
                activity=RedisSetupActivity.defn,
                arg=RedisSetupActivityModel(
                    namespace=tenant,
                    product=ProductName,
                    redis_tenant_password=redis_tenant_password,
                ),
                retry_policy=RedisSetupActivity.get_retry_policy(),
                start_to_close_timeout=RedisSetupActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=OnePasswordCreateOrUpdateActivity.defn,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    secret_name="redis_password",
                    secret_value=redis_tenant_password,
                ),
                retry_policy=OnePasswordCreateOrUpdateActivity.get_retry_policy(),
                start_to_close_timeout=OnePasswordCreateOrUpdateActivity.get_timeout(),
            )

            tenant_config = "tenant-config.json"
            rclone_config = "rclone.conf"
            vector_config = "vector-config.toml"
            statestore_config = "statestore.yaml"
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
                {
                    "name": "jeeves-cli-vector-config",
                    "key": vector_config,
                    "template_file_name": f"{config.env}-vector-config.tmpl.toml",
                },
                {
                    "name": "jeeves-statestore-config",
                    "key": statestore_config,
                    "template_file_name": f"{config.env}-statestore.tmpl.yaml",
                },
            ]:
                await workflow.execute_activity(
                    activity=K8sConfigMapCreationActivity.defn,
                    arg=K8sConfigMapCreationActivityModel(
                        namespace=tenant,
                        name=config_map["name"],
                        template_file_name=config_map["template_file_name"],
                        destination_file_name=config_map["key"],
                        cloudflare_r2_folder_path="jeeves-config",
                        template_payload={"tenant": tenant},
                    ),
                    retry_policy=K8sConfigMapCreationActivity.get_retry_policy(),
                    start_to_close_timeout=K8sConfigMapCreationActivity.get_timeout(),
                )

            # dns setup for api
            await workflow.execute_activity(
                activity=CreateCloudflareDNSRecordActivity.defn,
                arg=CreateCloudflareDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{jeeves_config.domain_name}",
                    zone_id=jeeves_config.zone_id,
                    content=config.k8s_cname,
                ),
                retry_policy=CreateCloudflareDNSRecordActivity.get_retry_policy(),
                start_to_close_timeout=CreateCloudflareDNSRecordActivity.get_timeout(),
            )

            # create bucket
            bucket_name = f"{tenant}-{jeeves_config.domain_name.replace('.', '-')}"
            await workflow.execute_activity(
                activity=CreateCloudflareBucketActivity.defn,
                arg=CreateCloudflareBucketActivityModel(
                    bucket_name=bucket_name,
                ),
                retry_policy=CreateCloudflareBucketActivity.get_retry_policy(),
                start_to_close_timeout=CreateCloudflareBucketActivity.get_timeout(),
            )

            # link bucket to custom domain
            await workflow.execute_activity(
                activity=LinkBucketToDomainActivity.defn,
                arg=LinkBucketToDomainActivityModel(
                    bucket_name=bucket_name,
                    domain_name=f"{tenant}.{jeeves_config.domain_name}",
                    zone_id=jeeves_config.zone_id,
                ),
                retry_policy=LinkBucketToDomainActivity.get_retry_policy(),
                start_to_close_timeout=LinkBucketToDomainActivity.get_timeout(),
            )

            # propagate the dns record
            await workflow.execute_activity(
                activity=PropagateDNSRecordActivity.defn,
                arg=PropagateDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{jeeves_config.domain_name}",
                ),
                retry_policy=PropagateDNSRecordActivity.get_retry_policy(),
                start_to_close_timeout=PropagateDNSRecordActivity.get_timeout(),
            )

            repo_name = "jeeves-ui"
            if config.env == "production":
                image_tag = "production"
                dest_dir = f"{bucket_name}/"
            else:
                image_tag = "sprint"
                dest_dir = f"{bucket_name}/{image_tag}"

            docker_image = f"registry.314ecorp.tech/jeeves-app:{image_tag}"

            src_object_name = f"{repo_name}/{image_tag}/bundle.zip"

            bundle_path = "bundle/dist/admin"

            # copy artifacts to bucket
            await workflow.execute_activity(
                activity=CopyArtifactsToBucketActivity.defn,
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

            realm_name = tenant
            # keycloak realm setup
            await workflow.execute_activity(
                activity=KeycloakRealmSetupActivity.defn,
                arg=KeycloakRealmSetupActivityModel(
                    realm_name=realm_name,
                    domain=jeeves_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_realm.json",
                ),
                retry_policy=KeycloakRealmSetupActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakRealmSetupActivity.get_timeout(),
            )

            # keycloak client setup
            await workflow.execute_activity(
                activity=KeycloakClientSetupActivity.defn,
                arg=KeycloakClientSetupActivityModel(
                    tenant=tenant,
                    realm_name=realm_name,
                    domain=jeeves_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_jeeves_client.json",
                ),
                retry_policy=KeycloakClientSetupActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakClientSetupActivity.get_timeout(),
            )

            roles = [
                "_access-manage-todos",
                "_access-manage-alerts",
                "_access-settings",
                "_allow-delete-assets",
                "_allow-add-edit-assets",
                "_access-reports",
                "_allow-view-assets",
                "_JEEVESALL",
                "_allow-conversion-tools",
                "_developer",
                "_access-screen-recorder",
                "_allow-standalone-launch",
                "_allow-publish-assets",
                "_can-manage-activities",
                "_allow-add-edit-courses",
                "_allow-delete-courses",
                "_allow-enroll-courses",
                "_allow-view-all-courses",
            ]
            # keycloak client roles setup
            await workflow.execute_activity(
                activity=KeycloakCreateClientRolesActivity.defn,
                arg=KeycloakCreateClientRolesActivityModel(
                    client_name="jeeves",
                    realm_name=realm_name,
                    roles=roles,
                ),
                retry_policy=KeycloakCreateClientRolesActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakCreateClientRolesActivity.get_timeout(),
            )

            # keycloak tenant customer admin user setup
            await workflow.execute_activity(
                activity=KeycloakCreateTenantCustomerAdminUserActivity.defn,
                arg=KeycloakCreateTenantCustomerAdminUserActivityModel(
                    realm_name=realm_name,
                    client_name="jeeves",
                    username=email,
                    email=email,
                    firstname=first_name,
                    lastname=last_name,
                    template_path=TemplatePath,
                    template_name="keycloak_tenant_customer_admin.json",
                ),
                retry_policy=KeycloakCreateTenantCustomerAdminUserActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakCreateTenantCustomerAdminUserActivity.get_timeout(),
            )

            # keycloak internal users setup
            await workflow.execute_activity(
                activity=KeycloakCreateInternalUsersActivity.defn,
                arg=KeycloakCreateInternalUsersActivityModel(
                    realm_name=realm_name,
                    client_name="jeeves",
                    template_path=TemplatePath,
                    template_name="keycloak_tenant_internal_user.json",
                    users=orjson.loads(open(f"{TemplatePath}/{config.env}_internal_users.json").read()),
                ),
                retry_policy=KeycloakCreateInternalUsersActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakCreateInternalUsersActivity.get_timeout(),
            )

            # atlas job
            await workflow.execute_activity(
                activity=DatabaseMigrationJobActivity.defn,
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
                retry_policy=DatabaseMigrationJobActivity.get_retry_policy(),
                start_to_close_timeout=DatabaseMigrationJobActivity.get_timeout(),
            )

            # vespa job
            await workflow.execute_activity(
                activity=VespaJobActivity.defn,
                arg=jeeves,
                retry_policy=VespaJobActivity.get_retry_policy(),
                start_to_close_timeout=VespaJobActivity.get_timeout(),
            )

            # kubernetes service
            await workflow.execute_activity(
                activity=KubernetesServiceActivity.defn,
                arg=KubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="jeeves",
                    ports={"http": 8000},
                ),
                retry_policy=KubernetesServiceActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesServiceActivity.get_timeout(),
            )

            template_env = get_env(template_path=TemplatePath)

            template = template_env.get_template("istio-rules.json")
            output = template.render(tenant=tenant, image_tag=image_tag, env=config.env)

            http_list = orjson.loads(output)
            if config.env != "production":
                http_list.append(
                    {
                        "name": "redirect",
                        "match": [{"uri": {"exact": "/"}}],
                        "redirect": {"uri": f"/{image_tag}/"},
                    }
                )

            # kubernetes virtual service
            await workflow.execute_activity(
                activity=KubernetesIstioVirtualServiceActivity.defn,
                arg=KubernetesIstioVirtualServiceActivityModel(
                    namespace=tenant,
                    host=f"{tenant}.api.{jeeves_config.domain_name}",
                    service_name="jeeves-vs",
                    payload=http_list,
                ),
                retry_policy=KubernetesIstioVirtualServiceActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesIstioVirtualServiceActivity.get_timeout(),
            )

            dynamic_url_hash_key = await workflow.execute_activity(
                activity=OnePasswordGetActivity.defn,
                arg=OnePasswordGetActivityModel(
                    tenant="INTEGRATION_COMMON_CONFIG" if config.env != "production" else "PRODUCTION_COMMON_CONFIG",
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    secret_name="dynamic_url_hash_key",
                ),
                retry_policy=OnePasswordGetActivity.get_retry_policy(),
                start_to_close_timeout=OnePasswordGetActivity.get_timeout(),
            )

            # statefulset pod creation for server
            await workflow.execute_activity(
                activity=KubernetesStatefulSetActivity.defn,
                arg=KubernetesStatefulSetActivityModel(
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
                        {
                            "name": "statestore-volume",
                            "mount_path": f"/root/.dapr/components/{statestore_config}",
                            "sub_path": statestore_config,
                        },
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
                        {
                            "name": "statestore-volume",
                            "config_map_name": "jeeves-statestore-config",
                            "key": statestore_config,
                            "path": statestore_config,
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
                retry_policy=KubernetesStatefulSetActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesStatefulSetActivity.get_timeout(),
            )

            # statefulset pod creation for cli
            await workflow.execute_activity(
                activity=KubernetesStatefulSetActivity.defn,
                arg=KubernetesStatefulSetActivityModel(
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
                        {
                            "name": "statestore-volume",
                            "mount_path": f"/root/.dapr/components/{statestore_config}",
                            "sub_path": statestore_config,
                        },
                        {"name": "vector-volume", "mount_path": "/vector", "read_only": True},
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
                        {
                            "name": "statestore-volume",
                            "config_map_name": "jeeves-statestore-config",
                            "key": statestore_config,
                            "path": statestore_config,
                        },
                        {
                            "name": "vector-volume",
                            "config_map_name": "jeeves-cli-vector-config",
                            "key": vector_config,
                            "path": vector_config,
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
                retry_policy=KubernetesStatefulSetActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesStatefulSetActivity.get_timeout(),
            )

            # delete deployment if exists (for update)
            await workflow.execute_activity(
                activity=DeploymentDeletionActivity.defn,
                arg=DeploymentDeletionActivityModel(
                    namespace=tenant,
                    name="jeeves",
                ),
                retry_policy=DeploymentDeletionActivity.get_retry_policy(),
                start_to_close_timeout=DeploymentDeletionActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=DeploymentDeletionActivity.defn,
                arg=DeploymentDeletionActivityModel(
                    namespace=tenant,
                    name="jeeves-worker",
                ),
                retry_policy=DeploymentDeletionActivity.get_retry_policy(),
                start_to_close_timeout=DeploymentDeletionActivity.get_timeout(),
            )

            # vm pod scraper
            await workflow.execute_activity(
                activity=VMPodScrapperActivity.defn,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="jeeves-metrics",
                    app="jeeves",
                    path="/metrics/",
                    interval="15s",
                ),
                retry_policy=VMPodScrapperActivity.get_retry_policy(),
                start_to_close_timeout=VMPodScrapperActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=VMPodScrapperActivity.defn,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="jeeves-worker-metrics",
                    app="jeeves",
                    path="/metrics/",
                    interval="15s",
                ),
                retry_policy=VMPodScrapperActivity.get_retry_policy(),
                start_to_close_timeout=VMPodScrapperActivity.get_timeout(),
            )

            # temporal namespace creation
            await workflow.execute_activity(
                activity=TemporalNamespaceActivity.defn,
                arg=TemporalNamespaceActivityModel(
                    namespace=f"jeeves_{tenant}",
                ),
                retry_policy=TemporalNamespaceActivity.get_retry_policy(),
                start_to_close_timeout=TemporalNamespaceActivity.get_timeout(),
            )

            # ai voice setup
            await workflow.execute_activity(
                activity=AiVoiceSetupActivity.defn,
                arg=AiVoiceSetupActivityModel(
                    tenant=tenant,
                    config=jeeves_config,
                ),
                retry_policy=AiVoiceSetupActivity.get_retry_policy(),
                start_to_close_timeout=AiVoiceSetupActivity.get_timeout(),
            )

            # preload assets job
            await workflow.execute_activity(
                activity=PreloadAssetsJobActivity.defn,
                arg=jeeves,
                retry_policy=PreloadAssetsJobActivity.get_retry_policy(),
                start_to_close_timeout=PreloadAssetsJobActivity.get_timeout(),
            )

            # check pod running status
            for pod in ["jeeves", "jeeves-worker"]:
                await workflow.execute_activity(
                    activity=CheckPodRunningStatusActivity.defn,
                    arg=CheckPodRunningStatusActivityModel(
                        namespace=tenant,
                        name=pod,
                    ),
                    retry_policy=CheckPodRunningStatusActivity.get_retry_policy(),
                    start_to_close_timeout=CheckPodRunningStatusActivity.get_timeout(),
                )

            # update tenant status
            await workflow.execute_activity(
                activity=UpdateTenantStatusActivity.defn,
                arg=TenantStatus(tenant_name=tenant, status="Completed", product=ProductName),
                retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
                start_to_close_timeout=UpdateTenantStatusActivity.get_timeout(),
            )

            # send mail
            if not is_deployment:
                await workflow.execute_activity(
                    activity=SendAfterProvisioningMailActivity.defn,
                    arg=SendAfterProvisioningMailActivityModel(
                        realm_name=realm_name,
                        tenant=tenant,
                        user_details={
                            "firstName": first_name,
                            "lastName": last_name,
                            "email": email,
                        },
                        domain_name=jeeves_config.domain_name,
                        product=ProductName,
                        from_name=jeeves_config.sender_name,
                        email_from=jeeves_config.sender_email,
                    ),
                    retry_policy=SendAfterProvisioningMailActivity.get_retry_policy(),
                    start_to_close_timeout=SendAfterProvisioningMailActivity.get_timeout(),
                )

        except Exception as e:
            workflow.logger.error(f"Error in onboarding workflow: {e}")
            await workflow.execute_activity(
                activity=UpdateTenantStatusActivity.defn,
                arg=TenantStatus(
                    tenant_name=tenant,
                    status="Failed" if not is_deployment else "DeploymentFailed",
                    error_msg=str(e),
                    product=ProductName,
                ),
                retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
                start_to_close_timeout=UpdateTenantStatusActivity.get_timeout(),
            )
            await workflow.execute_activity(
                activity=SlackNotificationActivity.defn,
                arg=SlackNotificationActivityModel(
                    product=ProductName,
                    error_message=str(e),
                ),
                retry_policy=SlackNotificationActivity.get_retry_policy(),
                start_to_close_timeout=SlackNotificationActivity.get_timeout(),
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
