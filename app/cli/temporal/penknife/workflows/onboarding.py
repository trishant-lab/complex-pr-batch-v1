from collections.abc import Callable
from datetime import timedelta
import orjson
import pydash
from temporalio import workflow

from app.cli.temporal.activities.cloudflareSetup import (
    CreateCloudflareBucketActivity,
    CreateCloudflareBucketActivityModel,
    CreateCloudflareDNSRecordActivity,
    CreateCloudflareDNSRecordActivityModel,
    LinkBucketToDomainActivity,
    LinkBucketToDomainActivityModel,
    PenknifeCopyArtifactsToBucketActivity,
    PenknifeCopyArtifactsToBucketActivityModel,
    PropagateDNSRecordActivity,
    PropagateDNSRecordActivityModel,
)
from app.cli.temporal.activities.databaseMigrationJob import (
    DatabaseMigrationJobActivity,
    DatabaseMigrationJobActivityModel,
)
from app.cli.temporal.activities.k8sIstioVirtualService import (
    KubernetesIstioVirtualServiceActivity,
    KubernetesIstioVirtualServiceActivityModel,
)
from app.cli.temporal.activities.k8sSecret import K8sSecretCreationActivity, K8sSecretCreationActivityModel
from app.cli.temporal.activities.k8sService import KubernetesServiceActivity, KubernetesServiceActivityModel
from app.cli.temporal.activities.k8sconfigMap import K8sConfigMapCreationActivity, K8sConfigMapCreationActivityModel
from app.cli.temporal.activities.k8snamespace import K8sNamespaceCreationActivity, K8sNamespaceCreationActivityModel
from app.cli.temporal.activities.keycloakSetup import (
    KeycloakClientSetupActivity,
    KeycloakClientSetupActivityModel,
    KeycloakCreateClientRolesActivity,
    KeycloakCreateClientRolesActivityModel,
    KeycloakCreateIDPFlowActivity,
    KeycloakCreateTenantCustomerAdminUserActivity,
    KeycloakCreateTenantCustomerAdminUserActivityModel,
    KeycloakRealmSetupActivity,
    KeycloakRealmSetupActivityModel,
)
from app.cli.temporal.activities.onePassword import (
    OnePasswordCreateOrUpdateActivity,
    OnePasswordCreateOrUpdateActivityModel,
)
from app.cli.temporal.activities.penknifeNovuSetup import PenknifeNovuSetupActivity
from app.cli.temporal.activities.penknifeUserSetup import PenknifeUserSetupActivity
from app.cli.temporal.activities.postgresSetup import (
    KeycloakUserMappingActivity,
    KeycloakUserMappingActivityModel,
    MatomoUserMappingActivity,
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
    TableSpaceActivity,
    TableSpaceActivityModel,
)
from app.cli.temporal.activities.redis import RedisSetupActivity, RedisSetupActivityModel
from app.cli.temporal.activities.sendMail import (
    # SendAfterProvisioningMailActivity,
    # SendAfterProvisioningMailActivityModel,
    SendBeforeProvisioningMailActivity,
    SendBeforeProvisioningMailActivityModel,
)
from app.cli.temporal.activities.statefulSetPodCreation import (
    KubernetesStatefulSetActivity,
    KubernetesStatefulSetActivityModel,
)
from app.cli.temporal.activities.temporalNamespace import TemporalNamespaceActivity, TemporalNamespaceActivityModel
from app.cli.temporal.activities.updateTenantStatus import TenantStatus, UpdateTenantStatusActivity
from app.cli.temporal.activities.vmPodScrapper import VMPodScrapperActivity, VMPodScrapperActivityModel
from app.cli.temporal.core.base import Workflow
from app.cli.temporal.penknife.models.penknifespec import PenknifeSpec, TenantType
from app.cli.temporal.penknife import TemplatePath

with workflow.unsafe.imports_passed_through():
    from app.common import generate_password
    from app.core.settings import AppSettings, PenknifeSettings, get_settings
    from app.template_env import get_env


ProductName = "penknife"
OnePasswordVaultName = "Penknife"


@workflow.defn(name="PenknifeOnboardingWorkflow", sandboxed=False)
class PenknifeOnboardingWorkflow(Workflow):
    """
    Penknife Onboarding Workflow
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
            OnePasswordCreateOrUpdateActivity.defn,
            UpdateTenantStatusActivity.defn,
            # SendAfterProvisioningMailActivity.defn,
            VMPodScrapperActivity.defn,
            TemporalNamespaceActivity.defn,
            PostgresUserCreationActivity.defn,
            PostgresSupavisorPollUserActivity.defn,
            PostgresSchemaCreationActivity.defn,
            PostgresGrantAccessToUserActivity.defn,
            KeycloakUserMappingActivity.defn,
            MatomoUserMappingActivity.defn,
            PostgresGrantAllPrivilegesOnTableActivity.defn,
            TableSpaceActivity.defn,
            K8sNamespaceCreationActivity.defn,
            K8sSecretCreationActivity.defn,
            PenknifeNovuSetupActivity.defn,
            RedisSetupActivity.defn,
            KeycloakRealmSetupActivity.defn,
            KeycloakClientSetupActivity.defn,
            KeycloakCreateIDPFlowActivity.defn,
            KeycloakCreateTenantCustomerAdminUserActivity.defn,
            KeycloakCreateClientRolesActivity.defn,
            K8sConfigMapCreationActivity.defn,
            CreateCloudflareDNSRecordActivity.defn,
            PenknifeCopyArtifactsToBucketActivity.defn,
            CreateCloudflareBucketActivity.defn,
            LinkBucketToDomainActivity.defn,
            PropagateDNSRecordActivity.defn,
            DatabaseMigrationJobActivity.defn,
            KubernetesStatefulSetActivity.defn,
            KubernetesServiceActivity.defn,
            KubernetesIstioVirtualServiceActivity.defn,
            PenknifeUserSetupActivity.defn
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", penknife: PenknifeSpec) -> str:
        """
        Return workflow id
        """
        return f"{ProductName}_onboarding_workflow_{pydash.get(penknife, 'tenant')}"

    @workflow.run
    async def run(self: "Workflow", penknife: PenknifeSpec) -> None:
        """
        Run the workflow
        """
        config: AppSettings = get_settings()
        penknife_config: PenknifeSettings = config.penknife

        first_name = pydash.get(penknife, "firstName")
        last_name = pydash.get(penknife, "lastName")
        email = pydash.get(penknife, "email")
        tenant = pydash.get(penknife, "tenant")
        tenant_type = pydash.get(penknife, "tenantType")
        tenant_type = TenantType.get_tenant_type(tenant_type)

        try:
            if not pydash.get(penknife, "emailSent"):
                await workflow.execute_activity(
                    activity=SendBeforeProvisioningMailActivity.defn,
                    arg=SendBeforeProvisioningMailActivityModel(
                        user_details={
                            "firstName": first_name,
                            "lastName": last_name,
                            "email": email,
                        },
                        product=ProductName,
                        from_name=penknife_config.sender_name,
                        email_from=penknife_config.sender_email,
                    ),
                    retry_policy=SendBeforeProvisioningMailActivity.get_retry_policy(),
                    start_to_close_timeout=SendBeforeProvisioningMailActivity.get_timeout(),
                )

            # Wait for approval or denial
            await workflow.wait_condition(lambda: self.approved or self.deny)

            if self.deny:
                await workflow.execute_activity(
                    activity=UpdateTenantStatusActivity.defn,
                    arg=TenantStatus(
                        tenant_name=pydash.get(penknife, "tenant"),
                        status="Declined",
                        error_msg="Request Declined",
                    ),
                    retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
                    start_to_close_timeout=timedelta(seconds=120),
                )
                return

            postgres_schema_name = tenant
            postgres_database_name = "penknife"
            postgres_username = f"{ProductName}_{tenant}"
            postgres_password = generate_password(length=20)
            image_tag = "production" if config.env == "production" else "sprint"
            docker_image = f"registry.314ecorp.tech/penknife-app:{image_tag}"

            await workflow.execute_activity(
                activity=OnePasswordCreateOrUpdateActivity.defn,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item="application-config",
                    vault=OnePasswordVaultName,
                    secret_name="pg_password",
                    secret_value=postgres_password,
                ),
                retry_policy=OnePasswordCreateOrUpdateActivity.get_retry_policy(),
                start_to_close_timeout=OnePasswordCreateOrUpdateActivity.get_timeout(),
            )

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

            # await workflow.execute_activity(
            #     activity=MatomoUserMappingActivity.defn,
            #     arg=MatomoUserMappingActivityModel(
            #         username=postgres_username,
            #         database_name=postgres_database_name,
            #     ),
            #     retry_policy=MatomoUserMappingActivity.get_retry_policy(),
            #     start_to_close_timeout=MatomoUserMappingActivity.get_timeout(),
            # )

            await workflow.execute_activity(
                activity=PostgresGrantAllPrivilegesOnTableActivity.defn,
                arg=PostgresGrantAllPrivilegesOnTableActivityModel(
                    database_name=postgres_database_name,
                    username=postgres_username,
                    tables=["user_entity", "realm"],
                ),
                retry_policy=PostgresGrantAllPrivilegesOnTableActivity.get_retry_policy(),
                start_to_close_timeout=PostgresGrantAllPrivilegesOnTableActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=TableSpaceActivity.defn,
                arg=TableSpaceActivityModel(
                    username=postgres_username,
                    database_name=postgres_database_name,
                ),
                retry_policy=TableSpaceActivity.get_retry_policy(),
                start_to_close_timeout=TableSpaceActivity.get_timeout(),
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

            await workflow.execute_activity(
                activity=PenknifeNovuSetupActivity.defn,
                arg=penknife,
                retry_policy=PenknifeNovuSetupActivity.get_retry_policy(),
                start_to_close_timeout=PenknifeNovuSetupActivity.get_timeout(),
            )

            redis_tenant_password = generate_password(length=20)

            await workflow.execute_activity(
                activity=OnePasswordCreateOrUpdateActivity.defn,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item="application-config",
                    vault=OnePasswordVaultName,
                    secret_name="redis_password",
                    secret_value=redis_tenant_password,
                ),
                retry_policy=OnePasswordCreateOrUpdateActivity.get_retry_policy(),
                start_to_close_timeout=OnePasswordCreateOrUpdateActivity.get_timeout(),
            )

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

            realm_name = tenant
            # keycloak realm setup
            await workflow.execute_activity(
                activity=KeycloakRealmSetupActivity.defn,
                arg=KeycloakRealmSetupActivityModel(
                    realm_name=realm_name,
                    domain=penknife_config.domain_name,
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
                    domain=penknife_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_penknife_client.json",
                ),
                retry_policy=KeycloakClientSetupActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakClientSetupActivity.get_timeout(),
            )

            # todo: add the rest of the activities for keycloak
            # Setup keycloak auth client
            auth_credential = generate_password(length=32)

            await workflow.execute_activity(
                activity=OnePasswordCreateOrUpdateActivity.defn,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item="application-config",
                    vault=OnePasswordVaultName,
                    secret_name="auth_credential",
                    secret_value=auth_credential,
                ),
                retry_policy=OnePasswordCreateOrUpdateActivity.get_retry_policy(),
                start_to_close_timeout=OnePasswordCreateOrUpdateActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=KeycloakClientSetupActivity.defn,
                arg=KeycloakClientSetupActivityModel(
                    tenant=tenant,
                    realm_name=realm_name,
                    domain=penknife_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_penknife_auth_client.json",
                    auth_credential=auth_credential,
                ),
                retry_policy=KeycloakClientSetupActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakClientSetupActivity.get_timeout(),
            )

            roles = [
                "_broadcast-mail",
                "_bulk-account",
                "_bulk-application",
                "_bulk-candidate",
                "_bulk-contact",
                "_bulk-jobs",
                "_bulk-opportunity",
                "_bulk-placement",
                "_bulk-staticlist",
                "_delete-account",
                "_delete-application",
                "_delete-candidate",
                "_delete-contact",
                "_delete-jobs",
                "_delete-opportunity",
                "_delete-placement",
                "_delete-staticlist",
                "_export-account",
                "_export-application",
                "_export-candidate",
                "_export-contact",
                "_export-jobs",
                "_export-opportunity",
                "_export-placement",
                "_manage-activities",
                "_manage-assessment-cards",
                "_manage-career-portal",
                "_manage-company",
                "_manage-duplicates",
                "_manage-email-settings",
                "_manage-fields",
                "_manage-integrations",
                "_manage-listofvalues",
                "_manage-locations-departments",
                "_manage-pipelines",
                "_manage-screening-questionnaire",
                "_manage-teams",
                "_manage-workflows",
                "_penknife-admin",
                "_send-mail",
                "_view-account",
                "_view-application",
                "_view-candidate",
                "_view-contact",
                "_view-imports",
                "_view-insights",
                "_view-jobs",
                "_view-others-saved-search",
                "_view-opportunity",
                "_view-placement",
                "_view-staticlist",
                "_workspace-admin",
                "_write-account",
                "_write-application",
                "_write-candidate",
                "_write-contact",
                "_write-jobs",
                "_write-opportunity",
                "_write-placement",
                "_write-staticlist",
            ]

            # keycloak client roles setup
            await workflow.execute_activity(
                activity=KeycloakCreateClientRolesActivity.defn,
                arg=KeycloakCreateClientRolesActivityModel(
                    client_name="penknife",
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
                    client_name="penknife",
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

            # Create IDP and flows in keycloak
            await workflow.execute_activity(
                activity=KeycloakCreateIDPFlowActivity.defn,
                arg=KeycloakClientSetupActivityModel(
                    tenant=tenant,
                    realm_name=realm_name,
                    domain=penknife_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_idp_and_flows.json",
                ),
                retry_policy=KeycloakCreateIDPFlowActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakCreateIDPFlowActivity.get_timeout(),
            )

            # setup tenant configmap
            for config_map in [
                {"name": "penknife-tenant-config", "key": "tenant-config.json"},
                {"name": "penknife-cli-vector-config", "key": "vector-config.toml"},
                {"name": "penknife-statestore-config", "key": "statestore.yaml"},
            ]:
                await workflow.execute_activity(
                    activity=K8sConfigMapCreationActivity.defn,
                    arg=K8sConfigMapCreationActivityModel(
                        namespace=tenant,
                        name=config_map["name"],
                        template_file_name=config_map["key"],
                        bucket_name="penknife-config",
                        template_payload={
                            "tenant": tenant,
                            "tenant_type": tenant_type,
                            "domain": penknife_config.domain_name,
                        },
                    ),
                    retry_policy=K8sConfigMapCreationActivity.get_retry_policy(),
                    start_to_close_timeout=K8sConfigMapCreationActivity.get_timeout(),
                )

            # dns setup for api
            await workflow.execute_activity(
                activity=CreateCloudflareDNSRecordActivity.defn,
                arg=CreateCloudflareDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{penknife_config.domain_name}",
                    zone_id=penknife_config.zone_id,
                ),
                retry_policy=CreateCloudflareDNSRecordActivity.get_retry_policy(),
                start_to_close_timeout=CreateCloudflareDNSRecordActivity.get_timeout(),
            )

            # create bucket
            bucket_name = f"{tenant}-{penknife_config.domain_name.replace('.', '-')}"
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
                    domain_name=f"{tenant}.{penknife_config.domain_name}",
                    zone_id=penknife_config.zone_id,
                ),
                retry_policy=LinkBucketToDomainActivity.get_retry_policy(),
                start_to_close_timeout=LinkBucketToDomainActivity.get_timeout(),
            )

            # for career portal

            # dns setup for api
            await workflow.execute_activity(
                activity=CreateCloudflareDNSRecordActivity.defn,
                arg=CreateCloudflareDNSRecordActivityModel(
                    domain_name=f"{tenant}-careers.api.{penknife_config.domain_name}",
                    zone_id=penknife_config.zone_id,
                ),
                retry_policy=CreateCloudflareDNSRecordActivity.get_retry_policy(),
                start_to_close_timeout=CreateCloudflareDNSRecordActivity.get_timeout(),
            )

            # create bucket
            careers_bucket_name = f"{tenant}-careers-{penknife_config.domain_name.replace('.', '-')}"
            await workflow.execute_activity(
                activity=CreateCloudflareBucketActivity.defn,
                arg=CreateCloudflareBucketActivityModel(
                    bucket_name=careers_bucket_name,
                ),
                retry_policy=CreateCloudflareBucketActivity.get_retry_policy(),
                start_to_close_timeout=CreateCloudflareBucketActivity.get_timeout(),
            )

            # link bucket to custom domain
            await workflow.execute_activity(
                activity=LinkBucketToDomainActivity.defn,
                arg=LinkBucketToDomainActivityModel(
                    bucket_name=careers_bucket_name,
                    domain_name=f"{tenant}-careers.{penknife_config.domain_name}",
                    zone_id=penknife_config.zone_id,
                ),
                retry_policy=LinkBucketToDomainActivity.get_retry_policy(),
                start_to_close_timeout=LinkBucketToDomainActivity.get_timeout(),
            )

            # This activity handle copy of artifacts of both main as well as careerportal
            repo_name = "penknife-ui"
            src_object_name = f"{repo_name}/{image_tag}/bundle.zip"

            await workflow.execute_activity(
                activity=PenknifeCopyArtifactsToBucketActivity.defn,
                arg=PenknifeCopyArtifactsToBucketActivityModel(
                    tenant=tenant,
                    bucket_name=bucket_name,
                    careerportal_bucket_name=careers_bucket_name,
                    src_object_name=src_object_name,
                    bundle_name="bundle.zip",
                ),
                retry_policy=PenknifeCopyArtifactsToBucketActivity.get_retry_policy(),
                start_to_close_timeout=PenknifeCopyArtifactsToBucketActivity.get_timeout(),
            )

            # Propagate both the dns record at last, since this is time taking process.

            # propagate the dns record
            await workflow.execute_activity(
                activity=PropagateDNSRecordActivity.defn,
                arg=PropagateDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{penknife_config.domain_name}",
                ),
                retry_policy=PropagateDNSRecordActivity.get_retry_policy(),
                start_to_close_timeout=PropagateDNSRecordActivity.get_timeout(),
            )

            # propagate the dns record
            await workflow.execute_activity(
                activity=PropagateDNSRecordActivity.defn,
                arg=PropagateDNSRecordActivityModel(
                    domain_name=f"{tenant}-careers.api.{penknife_config.domain_name}",
                ),
                retry_policy=PropagateDNSRecordActivity.get_retry_policy(),
                start_to_close_timeout=PropagateDNSRecordActivity.get_timeout(),
            )

            # database migration job

            await workflow.execute_activity(
                activity=DatabaseMigrationJobActivity.defn,
                arg=DatabaseMigrationJobActivityModel(
                    namespace=tenant,
                    job_name="penknife-db-schema-migration-job",
                    docker_image=docker_image,
                    volume_mounts=[
                        {
                            "name": "tenant-volume",
                            "mount_path": "/config/tenant-config.json",
                            "sub_path": "tenant-config.json",
                        },
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "penknife-tenant-config",
                            "key": "tenant-config.json",
                            "path": "tenant-config.json",
                        },
                    ],
                    container_envs=[
                        {"name": "APP_CONFIG_FILE", "value": "/config/tenant-config.json"},
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "CLIENT_CODE", "value": tenant},
                        {"name": "POSTGRES_PASSWORD", "value": postgres_password},
                        {"name": "POSTGRES_USER", "value": postgres_username},
                    ],
                    argument="python3 /app/atlas/atlas_script.py",
                    job_type="atlas",
                    product=ProductName,
                ),
                retry_policy=DatabaseMigrationJobActivity.get_retry_policy(),
                start_to_close_timeout=DatabaseMigrationJobActivity.get_timeout(),
            )

            # kubernetes service
            await workflow.execute_activity(
                activity=KubernetesServiceActivity.defn,
                arg=KubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="penknife",
                    port=8000,
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
                    host=f"{tenant}.api.{penknife_config.domain_name}",
                    service_name="penknife-vs",
                    payload=http_list,
                ),
                retry_policy=KubernetesIstioVirtualServiceActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesIstioVirtualServiceActivity.get_timeout(),
            )

            # kubernetes virtual service for careers
            template_career = template_env.get_template("istio-rules-careers.json")
            output_career = template_career.render(tenant=tenant, image_tag=image_tag, env=config.env)

            http_list_career = orjson.loads(output_career)

            await workflow.execute_activity(
                activity=KubernetesIstioVirtualServiceActivity.defn,
                arg=KubernetesIstioVirtualServiceActivityModel(
                    namespace=tenant,
                    host=f"{tenant}-careers.api.{penknife_config.domain_name}",
                    service_name="penknife-careers-vs",
                    payload=http_list_career,
                ),
                retry_policy=KubernetesIstioVirtualServiceActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesIstioVirtualServiceActivity.get_timeout(),
            )

            # statefulset pod creation for server
            await workflow.execute_activity(
                activity=KubernetesStatefulSetActivity.defn,
                arg=KubernetesStatefulSetActivityModel(
                    namespace=tenant,
                    name="penknife",
                    docker_image=docker_image,
                    request_resource={
                        "cpu": pydash.get(penknife, "serverSpec.request_cpu"),
                        "memory": pydash.get(penknife, "serverSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(penknife, "serverSpec.limit_cpu"),
                        "memory": pydash.get(penknife, "serverSpec.limit_memory"),
                    },
                    container_ports=[8000],
                    volume_mounts=[
                        {
                            "name": "tenant-volume",
                            "mount_path": "/config/tenant-config.json",
                            "sub_path": "tenant-config.json",
                        },
                        {
                            "name": "statestore-volume",
                            "mount_path": "/root/.dapr/components/statestore.yaml",
                            "sub_path": "statestore.yaml",
                        },
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "penknife-tenant-config",
                            "key": "tenant-config.json",
                            "path": "tenant-config.json",
                        },
                        {
                            "name": "statestore-volume",
                            "config_map_name": "penknife-statestore-config",
                            "key": "statestore.yaml",
                            "path": "statestore.yaml",
                        },
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "WEB_CONCURRENCY", "value": "5"},
                        {"name": "APP_CONFIG_FILE", "value": "/config/tenant-config.json"},
                        {"name": "IS_CLI", "value": "FALSE"},
                        {"name": "EXTRACTOR_ENABLED", "value": "FALSE"},
                    ],
                ),
                retry_policy=KubernetesStatefulSetActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesStatefulSetActivity.get_timeout(),
            )

            # statefulset pod creation for server

            # statefulset pod creation for cli
            await workflow.execute_activity(
                activity=KubernetesStatefulSetActivity.defn,
                arg=KubernetesStatefulSetActivityModel(
                    namespace=tenant,
                    name="penknife-cli",
                    docker_image=docker_image,
                    request_resource={
                        "cpu": pydash.get(penknife, "cliSpec.request_cpu"),
                        "memory": pydash.get(penknife, "cliSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(penknife, "cliSpec.limit_cpu"),
                        "memory": pydash.get(penknife, "cliSpec.limit_memory"),
                    },
                    container_ports=[8000],
                    volume_mounts=[
                        {
                            "name": "tenant-volume",
                            "mount_path": "/config/tenant-config.json",
                            "sub_path": "tenant-config.json",
                        },
                        {
                            "name": "statestore-volume",
                            "mount_path": "/root/.dapr/components/statestore.yaml",
                            "sub_path": "statestore.yaml",
                        },
                        {
                            "name": "vector-volume",
                            "mount_path": "/vector",
                            "read_only": True,
                        },
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "penknife-tenant-config",
                            "key": "tenant-config.json",
                            "path": "tenant-config.json",
                        },
                        {
                            "name": "statestore-volume",
                            "config_map_name": "penknife-statestore-config",
                            "key": "statestore.yaml",
                            "path": "statestore.yaml",
                        },
                        {
                            "name": "vector-volume",
                            "config_map_name": "penknife-cli-vector-config",
                            "key": "vector-config.toml",
                            "path": "vector-config.toml",
                        },
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "APP_CONFIG_FILE", "value": "/config/tenant-config.json"},
                        {"name": "IS_CLI", "value": "TRUE"},
                        {"name": "EXTRACTOR_ENABLED", "value": "TRUE"},
                        {"name": "IS_TEMPORAL_WORKER", "value": "TRUE"},
                        {"name": "VECTOR_LOG", "value": "off"},
                    ],
                ),
                retry_policy=KubernetesStatefulSetActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesStatefulSetActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=VMPodScrapperActivity.defn,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="penknife-metrics",
                    app="penknife",
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
                    namespace=f"penknife_{tenant}",
                ),
                retry_policy=TemporalNamespaceActivity.get_retry_policy(),
                start_to_close_timeout=TemporalNamespaceActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=PenknifeUserSetupActivity.defn,
                arg=penknife,
                retry_policy=PenknifeUserSetupActivity.get_retry_policy(),
                start_to_close_timeout=PenknifeUserSetupActivity.get_timeout(),
            )

            # update tenant status
            await workflow.execute_activity(
                activity=UpdateTenantStatusActivity.defn,
                arg=TenantStatus(tenant_name=tenant, status="Completed", product=ProductName),
                retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
                start_to_close_timeout=UpdateTenantStatusActivity.get_timeout(),
            )

            # send mail
            # This activity is commented, since adding url and origin to google console need to be done manually, and there is no need of sending any temporary password.
            # await workflow.execute_activity(
            #     activity=SendAfterProvisioningMailActivity.defn,
            #     arg=SendAfterProvisioningMailActivityModel(
            #         realm_name=realm_name,
            #         tenant=tenant,
            #         user_details={
            #             "firstName": first_name,
            #             "lastName": last_name,
            #             "email": email,
            #         },
            #         domain_name=penknife_config.domain_name,
            #         product=ProductName,
            #         from_name=penknife_config.sender_name,
            #         email_from=penknife_config.sender_email,
            #     ),
            #     retry_policy=SendAfterProvisioningMailActivity.get_retry_policy(),
            #     start_to_close_timeout=SendAfterProvisioningMailActivity.get_timeout(),
            # )

        except Exception as e:
            workflow.logger.error(f"Error in onboarding workflow: {e}")
            await workflow.execute_activity(
                activity=UpdateTenantStatusActivity.defn,
                arg=TenantStatus(
                    tenant_name=tenant,
                    status="Failed",
                    error_msg=str(e),
                    product=ProductName,
                ),
                retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
                start_to_close_timeout=UpdateTenantStatusActivity.get_timeout(),
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
