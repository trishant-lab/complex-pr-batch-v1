from collections.abc import Callable
from datetime import timedelta

import pydash
from temporalio import workflow

from app.cli.activity_util import run_activity
from app.cli.temporal.activities.cloudflare_setup import (
    CreateCloudflareBucketActivity,
    CreateCloudflareDNSRecordActivity,
    LinkBucketToDomainActivity,
    PenknifeCopyArtifactsToBucketActivity,
    PropagateDNSRecordActivity,
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
from app.cli.temporal.activities.k8s_namespace import K8sNamespaceCreationActivity, K8sNamespaceCreationActivityModel
from app.cli.temporal.activities.k8s_secret import K8sSecretCreationActivity, K8sSecretCreationActivityModel
from app.cli.temporal.activities.k8s_service import KubernetesServiceActivity, KubernetesServiceActivityModel
from app.cli.temporal.activities.keycloak_setup import (
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
from app.cli.temporal.activities.one_password import (
    OnePasswordCreateOrUpdateActivity,
    OnePasswordCreateOrUpdateActivityModel,
)
from app.cli.temporal.activities.penknife_novu_setup import PenknifeNovuSetupActivity
from app.cli.temporal.activities.penknife_user_setup import PenknifeUserSetupActivity
from app.cli.temporal.activities.postgres_setup import (
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
from app.cli.temporal.activities.send_mail import (
    SendBeforeProvisioningMailActivity,
    SendBeforeProvisioningMailActivityModel,
)
from app.cli.temporal.activities.stateful_set_pod_creation import (
    CheckPodRunningStatusActivity,
    CheckPodRunningStatusActivityModel,
)
from app.cli.temporal.activities.temporal_namespace import TemporalNamespaceActivity, TemporalNamespaceActivityModel
from app.cli.temporal.activities.update_tenant_status import TenantCliStatus, UpdateTenantStatusActivity
from app.cli.temporal.activities.vm_pod_scrapper import VMPodScrapperActivity, VMPodScrapperActivityModel
from app.cli.temporal.core.base import Workflow
from app.cli.temporal.models.cloudflare import (
    CreateCloudflareBucketActivityModel,
    CreateCloudflareDNSRecordActivityModel,
    LinkBucketToDomainActivityModel,
    PenknifeCopyArtifactsToBucketActivityModel,
    PropagateDNSRecordActivityModel,
)
from app.cli.temporal.penknife import TemplatePath
from app.cli.temporal.penknife.models.penknife_spec import PenknifeSpec, TenantType
from app.common import generate_password
from app.core.ijson import ijson_loads
from app.core.settings import AppSettings, PenknifeSettings, get_settings
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum
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
            KubernetesDeploymentActivity.defn,
            KubernetesServiceActivity.defn,
            KubernetesIstioVirtualServiceActivity.defn,
            PenknifeUserSetupActivity.defn,
            CheckPodRunningStatusActivity.defn,
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
                await run_activity(
                    activity=SendBeforeProvisioningMailActivity,
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
                )

            # Wait for approval or denial
            await workflow.wait_condition(lambda: self.approved or self.deny)

            if self.deny:
                await run_activity(
                    activity=UpdateTenantStatusActivity,
                    arg=TenantCliStatus(
                        tenant_name=pydash.get(penknife, "tenant"),
                        status=TenantStatusEnum.ApprovalDeclined,
                        error_msg="Request Declined",
                        product=ProductEnum.penknife,
                    ),
                    start_to_close_timeout=timedelta(seconds=120),
                )
                return

            postgres_schema_name = tenant
            postgres_database_name = "penknife"
            postgres_username = f"{ProductName}_{tenant}"
            postgres_password = generate_password(length=20)
            image_tag = "production" if config.env == "production" else "sprint"
            docker_image = f"registry.314ecorp.tech/penknife-app:{image_tag}"

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item="application-config",
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

            # await run_activity(
            #     activity=MatomoUserMappingActivity,
            #     arg=MatomoUserMappingActivityModel(
            #         username=postgres_username,
            #         database_name=postgres_database_name,
            #     ),
            # )

            await run_activity(
                activity=PostgresGrantAllPrivilegesOnTableActivity,
                arg=PostgresGrantAllPrivilegesOnTableActivityModel(
                    database_name=postgres_database_name,
                    username=postgres_username,
                    tables=["user_entity", "realm"],
                ),
            )

            await run_activity(
                activity=TableSpaceActivity,
                arg=TableSpaceActivityModel(
                    username=postgres_username,
                    database_name=postgres_database_name,
                ),
            )

            await run_activity(
                activity=K8sNamespaceCreationActivity,
                arg=K8sNamespaceCreationActivityModel(
                    namespace=tenant,
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

            # secret setup for postgres password
            await run_activity(
                activity=K8sSecretCreationActivity,
                arg=K8sSecretCreationActivityModel(
                    namespace=tenant,
                    name="postgres-password",
                    data={
                        "POSTGRES_PASSWORD": postgres_password,
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

            # await run_activity(
            #     activity=PenknifeNovuSetupActivity,
            #     arg=penknife,
            # )

            redis_tenant_password = generate_password(length=20)

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item="application-config",
                    vault=OnePasswordVaultName,
                    secret_name="redis_password",
                    secret_value=redis_tenant_password,
                ),
            )

            await run_activity(
                activity=RedisSetupActivity,
                arg=RedisSetupActivityModel(
                    namespace=tenant,
                    product=ProductName,
                    redis_tenant_password=redis_tenant_password,
                ),
            )

            realm_name = tenant
            # keycloak realm setup
            await run_activity(
                activity=KeycloakRealmSetupActivity,
                arg=KeycloakRealmSetupActivityModel(
                    realm_name=realm_name,
                    domain=penknife_config.domain_name,
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
                    domain=penknife_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_penknife_client.json",
                ),
            )

            # Setup keycloak auth client
            auth_credential = generate_password(length=32)

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item="application-config",
                    vault=OnePasswordVaultName,
                    secret_name="auth_credential",
                    secret_value=auth_credential,
                ),
            )

            await run_activity(
                activity=KeycloakClientSetupActivity,
                arg=KeycloakClientSetupActivityModel(
                    tenant=tenant,
                    realm_name=realm_name,
                    domain=penknife_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_penknife_auth_client.json",
                    auth_credential=auth_credential,
                ),
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
            await run_activity(
                activity=KeycloakCreateClientRolesActivity,
                arg=KeycloakCreateClientRolesActivityModel(
                    client_name="penknife",
                    realm_name=realm_name,
                    roles=roles,
                ),
            )

            # keycloak tenant customer admin user setup
            await run_activity(
                activity=KeycloakCreateTenantCustomerAdminUserActivity,
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
            )

            # Create IDP and flows in keycloak
            await run_activity(
                activity=KeycloakCreateIDPFlowActivity,
                arg=KeycloakClientSetupActivityModel(
                    tenant=tenant,
                    realm_name=realm_name,
                    domain=penknife_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_idp_and_flows.json",
                ),
            )
            tenant_config = "tenant-config.json"
            vector_config = "vector-config.toml"
            statestore_config = "statestore.yaml"

            # setup tenant configmap
            for config_map in [
                {
                    "name": "penknife-tenant-config",
                    "key": tenant_config,
                    "template_file_name": f"{config.env}-tenant-config.tmpl.json",
                },
                {
                    "name": "penknife-cli-vector-config",
                    "key": vector_config,
                    "template_file_name": f"{config.env}-vector-config.tmpl.toml",
                },
                {
                    "name": "penknife-statestore-config",
                    "key": statestore_config,
                    "template_file_name": f"{config.env}-statestore.tmpl.yaml",
                },
            ]:
                await run_activity(
                    activity=K8sConfigMapCreationActivity,
                    arg=K8sConfigMapCreationActivityModel(
                        namespace=tenant,
                        name=config_map["name"],
                        template_file_name=config_map["template_file_name"],
                        destination_file_name=config_map["key"],
                        bucket_name="penknife-config",
                        template_payload={
                            "tenant": tenant,
                            "tenant_type": tenant_type,
                            "domain": penknife_config.domain_name,
                        },
                    ),
                )

            # dns setup for api
            await run_activity(
                activity=CreateCloudflareDNSRecordActivity,
                arg=CreateCloudflareDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{penknife_config.domain_name}",
                    zone_id=penknife_config.zone_id,
                    content=config.k8s_cname,
                ),
            )

            # create bucket
            bucket_name = f"{tenant}-{penknife_config.domain_name.replace('.', '-')}"
            await run_activity(
                activity=CreateCloudflareBucketActivity,
                arg=CreateCloudflareBucketActivityModel(
                    bucket_name=bucket_name,
                ),
            )

            # link bucket to custom domain
            await run_activity(
                activity=LinkBucketToDomainActivity,
                arg=LinkBucketToDomainActivityModel(
                    bucket_name=bucket_name,
                    domain_name=f"{tenant}.{penknife_config.domain_name}",
                    zone_id=penknife_config.zone_id,
                ),
            )

            # for career portal

            # dns setup for api
            await run_activity(
                activity=CreateCloudflareDNSRecordActivity,
                arg=CreateCloudflareDNSRecordActivityModel(
                    domain_name=f"{tenant}-careers.api.{penknife_config.domain_name}",
                    zone_id=penknife_config.zone_id,
                    content=config.k8s_cname,
                ),
            )

            # create bucket
            careers_bucket_name = f"{tenant}-careers-{penknife_config.domain_name.replace('.', '-')}"
            await run_activity(
                activity=CreateCloudflareBucketActivity,
                arg=CreateCloudflareBucketActivityModel(
                    bucket_name=careers_bucket_name,
                ),
            )

            # link bucket to custom domain
            await run_activity(
                activity=LinkBucketToDomainActivity,
                arg=LinkBucketToDomainActivityModel(
                    bucket_name=careers_bucket_name,
                    domain_name=f"{tenant}-careers.{penknife_config.domain_name}",
                    zone_id=penknife_config.zone_id,
                ),
            )

            # This activity handle copy of artifacts of both main as well as careerportal
            repo_name = "penknife-ui"
            src_object_name = f"{repo_name}/{image_tag}/bundle.zip"

            await run_activity(
                activity=PenknifeCopyArtifactsToBucketActivity,
                arg=PenknifeCopyArtifactsToBucketActivityModel(
                    tenant=tenant,
                    bucket_name=bucket_name,
                    careerportal_bucket_name=careers_bucket_name,
                    src_object_name=src_object_name,
                    bundle_name="bundle.zip",
                ),
            )

            # Propagate both the dns record at last, since this is time taking process.

            # propagate the dns record
            await run_activity(
                activity=PropagateDNSRecordActivity,
                arg=PropagateDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{penknife_config.domain_name}",
                ),
            )

            # propagate the dns record
            await run_activity(
                activity=PropagateDNSRecordActivity,
                arg=PropagateDNSRecordActivityModel(
                    domain_name=f"{tenant}-careers.api.{penknife_config.domain_name}",
                ),
            )

            # database migration job
            tenant_config = "tenant-config.json"
            config_dir = "config"

            await run_activity(
                activity=DatabaseMigrationJobActivity,
                arg=DatabaseMigrationJobActivityModel(
                    namespace=tenant,
                    job_name="penknife-db-schema-migration-job",
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
                            "config_map_name": "penknife-tenant-config",
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
                    argument="python3 /app/atlas/atlas_script.py",
                    job_type="atlas",
                    product=ProductName,
                ),
            )

            # kubernetes service
            await run_activity(
                activity=KubernetesServiceActivity,
                arg=KubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="penknife",
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
                    host=f"{tenant}.api.{penknife_config.domain_name}",
                    service_name="penknife-vs",
                    payload=http_list,
                ),
            )

            # kubernetes virtual service for careers
            template_career = template_env.get_template("istio-rules-careers.json")
            output_career = template_career.render(tenant=tenant, image_tag=image_tag, env=config.env)

            http_list_career = ijson_loads(output_career)

            await run_activity(
                activity=KubernetesIstioVirtualServiceActivity,
                arg=KubernetesIstioVirtualServiceActivityModel(
                    namespace=tenant,
                    host=f"{tenant}-careers.api.{penknife_config.domain_name}",
                    service_name="penknife-careers-vs",
                    payload=http_list_career,
                ),
            )

            # statefulset pod creation for server
            await run_activity(
                activity=KubernetesDeploymentActivity,
                arg=KubernetesDeploymentActivityModel(
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
                    container_ports={"http": 8000},
                    volume_mounts=[
                        {
                            "name": "tenant-volume",
                            "mount_path": f"/{config_dir}/{tenant_config}",
                            "sub_path": tenant_config,
                        },
                        {
                            "name": "statestore-volume",
                            "mount_path": f"/root/.dapr/components/{statestore_config}",
                            "sub_path": statestore_config,
                        },
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "penknife-tenant-config",
                            "key": tenant_config,
                            "path": tenant_config,
                        },
                        {
                            "name": "statestore-volume",
                            "config_map_name": "penknife-statestore-config",
                            "key": statestore_config,
                            "path": statestore_config,
                        },
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "WEB_CONCURRENCY", "value": "5"},
                        {"name": "APP_CONFIG_FILE", "value": f"/{config_dir}/{tenant_config}"},
                        {"name": "IS_CLI", "value": "FALSE"},
                        {"name": "EXTRACTOR_ENABLED", "value": "FALSE"},
                    ],
                ),
            )

            # statefulset pod creation for server

            # statefulset pod creation for cli
            await run_activity(
                activity=KubernetesDeploymentActivity,
                arg=KubernetesDeploymentActivityModel(
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
                    container_ports={"http": 8000},
                    volume_mounts=[
                        {
                            "name": "tenant-volume",
                            "mount_path": f"/{config_dir}/{tenant_config}",
                            "sub_path": tenant_config,
                        },
                        {
                            "name": "statestore-volume",
                            "mount_path": f"/root/.dapr/components/{statestore_config}",
                            "sub_path": statestore_config,
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
                            "key": tenant_config,
                            "path": tenant_config,
                        },
                        {
                            "name": "statestore-volume",
                            "config_map_name": "penknife-statestore-config",
                            "key": statestore_config,
                            "path": statestore_config,
                        },
                        {
                            "name": "vector-volume",
                            "config_map_name": "penknife-cli-vector-config",
                            "key": vector_config,
                            "path": vector_config,
                        },
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "APP_CONFIG_FILE", "value": f"/{config_dir}/{tenant_config}"},
                        {"name": "IS_CLI", "value": "TRUE"},
                        {"name": "EXTRACTOR_ENABLED", "value": "TRUE"},
                        {"name": "IS_TEMPORAL_WORKER", "value": "TRUE"},
                        {"name": "VECTOR_LOG", "value": "off"},
                    ],
                ),
            )

            await run_activity(
                activity=VMPodScrapperActivity,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="penknife-metrics",
                    app="penknife",
                    path="/metrics/",
                    interval="15s",
                ),
            )

            # temporal namespace creation
            await run_activity(
                activity=TemporalNamespaceActivity,
                arg=TemporalNamespaceActivityModel(
                    namespace=f"penknife_{tenant}",
                ),
            )

            await run_activity(
                activity=PenknifeUserSetupActivity,
                arg=penknife,
            )

            # check pod running status
            for pod in ["penknife", "penknife-cli"]:
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
                    tenant_name=tenant, status=TenantStatusEnum.Provisioned, product=ProductEnum.penknife
                ),
            )

            # send mail
            # This activity is commented, since adding url and origin to google console need to be done manually, and
            # there is no need of sending any temporary password.
            # await run_activity(
            #     activity=SendAfterProvisioningMailActivity,
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
            # )

        except Exception as e:
            workflow.logger.error(f"Error in onboarding workflow: {e}")
            await run_activity(
                activity=UpdateTenantStatusActivity,
                arg=TenantCliStatus(
                    tenant_name=tenant,
                    status=TenantStatusEnum.ProvisioningFailed,
                    error_msg=str(e),
                    product=ProductEnum.penknife,
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
