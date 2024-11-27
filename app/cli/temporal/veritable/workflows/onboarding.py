from collections.abc import Callable
from app.cli.temporal.veritable import TemplatePath
import pydash
import orjson
from temporalio import workflow
from app.cli.temporal.activities.k8snamespace import K8sNamespaceCreationActivity, K8sNamespaceCreationActivityModel
from app.cli.temporal.activities.updateTenantStatus import TenantStatus, UpdateTenantStatusActivity
from app.cli.temporal.activities.k8sSecret import K8sSecretCreationActivity, K8sSecretCreationActivityModel
from app.cli.temporal.activities.redis import RedisSetupActivity, RedisSetupActivityModel
from app.cli.temporal.activities.k8sconfigMap import K8sConfigMapCreationActivity, K8sConfigMapCreationActivityModel
from app.cli.temporal.activities.k8sService import KubernetesServiceActivity, KubernetesServiceActivityModel
from app.cli.temporal.activities.vmPodScrapper import VMPodScrapperActivity, VMPodScrapperActivityModel
from app.cli.temporal.activities.temporalNamespace import (
    TemporalNamespaceActivity,
    TemporalNamespaceActivityModel,
)

from app.cli.temporal.core.base import Workflow
from app.cli.temporal.activities.postgresSetup import (
    PostgresDatabaseCreationActivity,
    PostgresUserCreationActivity,
    PostgresDatabaseCreationActivityModel,
    PostgresUserCreationActivityModel,
    PostgresGrantAccessToUserActivity,
    PostgresGrantAccessToUserActivityModel,
    PostgresSupavisorPollUserActivity,
    PostgresSupavisorPollUserActivityModel,
    PostgresSchemaCreationActivity,
    PostgresSchemaCreationActivityModel,
)
from app.cli.temporal.activities.k8sIstioVirtualService import (
    KubernetesIstioVirtualServiceActivity,
    KubernetesIstioVirtualServiceActivityModel,
)
from app.cli.temporal.activities.statefulSetPodCreation import (
    KubernetesStatefulSetActivity,
    KubernetesStatefulSetActivityModel,
)
from app.cli.temporal.activities.tenantCrd import (
    TenantCrdCreationActivity,
    TenantCrdCreationActivityModel,
    GetTenantCrdActivity,
    GetTenantCrdActivityModel,
)
from app.cli.temporal.activities.sendMail import (
    SendAfterProvisioningMailActivity,
    SendAfterProvisioningMailActivityModel,
    SendBeforeProvisioningMailActivity,
    SendBeforeProvisioningMailActivityModel,
)
from app.cli.temporal.activities.databaseMigrationJob import (
    DatabaseMigrationJobActivity,
    DatabaseMigrationJobActivityModel,
)
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
from app.cli.temporal.activities.keycloakSetup import (
    KeycloakCreateTenantCustomerAdminUserActivity,
    KeycloakCreateTenantCustomerAdminUserActivityModel,
    KeycloakRealmSetupActivity,
    KeycloakRealmSetupActivityModel,
)
from app.cli.temporal.veritable.models.veritableSpec import VeritableSpec

with workflow.unsafe.imports_passed_through():
    from app.common import generate_password
    from app.core.settings import AppSettings, VeritableSettings, get_settings
    from app.template_env import get_env


ProductName = "veritable"
OnePasswordVaultName = "veritable"


@workflow.defn
class VeritableOnboardingWorkflow(Workflow):
    """
    Veritable Onboarding Workflow
    """

    @staticmethod
    def get_activities() -> list[type[Callable]]:  # type: ignore
        """
        Return list of activities used in the workflow
        """
        return [
            GetTenantCrdActivity.defn,
            SendBeforeProvisioningMailActivity.defn,
            UpdateTenantStatusActivity.defn,
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
            LinkBucketToDomainActivity.defn,
            PropagateDNSRecordActivity.defn,
            CopyArtifactsToBucketActivity.defn,
            KeycloakRealmSetupActivity.defn,
            KeycloakCreateTenantCustomerAdminUserActivity.defn,
            DatabaseMigrationJobActivity.defn,
            KubernetesServiceActivity.defn,
            KubernetesIstioVirtualServiceActivity.defn,
            KubernetesStatefulSetActivity.defn,
            TemporalNamespaceActivity.defn,
            VMPodScrapperActivity.defn,
            SendAfterProvisioningMailActivity.defn,
            TenantCrdCreationActivity.defn,
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", veritable: VeritableSpec) -> str | None:
        """
        Return unique workflow id from workflow input, guarantees exactly one execution of workflow
        - Add combination of one or more fields from `workflow_input` to uniquely identify workflow
        """
        return f"veritable_onboarding_workflow_{pydash.get(veritable, 'tenant')}"

    @workflow.run
    async def run(self: "Workflow", veritable: VeritableSpec) -> None:
        """
        Entry point for workflow
        """
        config: AppSettings = get_settings()
        veritable_config: VeritableSettings = config.veritable
        first_name = pydash.get(veritable, "first_name")
        last_name = pydash.get(veritable, "last_name")
        email = pydash.get(veritable, "email")

        tenant = pydash.get(veritable, "tenant")
        # todo vaildate customer id

        try:
            # get tenant crd
            response = await workflow.execute_activity(
                activity=GetTenantCrdActivity.defn,
                arg=GetTenantCrdActivityModel(
                    tenant=tenant,
                    kind="VeritableTenant",
                    product=ProductName,
                ),
                retry_policy=GetTenantCrdActivity.get_retry_policy(),
                start_to_close_timeout=GetTenantCrdActivity.get_timeout(),
            )

            if [
                item
                for item in response.get("items", [])
                if response and item.get("metadata", {}).get("name") == tenant
            ]:
                raise Exception(f"Tenant {tenant} already exists")  # noqa: TRY301

            if not pydash.get(veritable, "emailSent"):
                await workflow.execute_activity(
                    activity=SendBeforeProvisioningMailActivity.defn,
                    arg=SendBeforeProvisioningMailActivityModel(
                        user_details={
                            "firstName": first_name,
                            "lastName": last_name,
                            "email": email,
                        },
                        product=ProductName,
                        from_name=veritable_config.sender_name,
                        email_from=veritable_config.sender_email,
                    ),
                    retry_policy=SendBeforeProvisioningMailActivity.get_retry_policy(),
                    start_to_close_timeout=SendBeforeProvisioningMailActivity.get_timeout(),
                )

            # Wait for approval or denial
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

            postgres_schema_name = tenant
            postgres_database_name = f"{ProductName}-{config.env}"
            postgres_username = f"{ProductName}_{tenant}"
            postgres_password = generate_password(length=20)
            redis_tenant_password = generate_password(length=20)
            image_tag = "production" if config.env == "production" else "sprint"
            docker_image = f"registry.314ecorp.tech/veritable-server:{image_tag}"
            template_env = get_env(template_path=TemplatePath)
            template = template_env.get_template("istio-rules.json")
            output = template.render(tenant=tenant, image_tag=image_tag)
            http_list = orjson.loads(output)
            if config.env != "production":
                http_list.append(
                    {
                        "name": "redirect",
                        "match": [{"uri": {"exact": "/"}}],
                        "redirect": {"uri": f"/{image_tag}/"},
                    }
                )

            # create namespace in k8s
            await workflow.execute_activity(
                activity=K8sNamespaceCreationActivity.defn,
                arg=K8sNamespaceCreationActivityModel(
                    namespace=tenant,
                ),
                retry_policy=K8sNamespaceCreationActivity.get_retry_policy(),
                start_to_close_timeout=K8sNamespaceCreationActivity.get_timeout(),
            )

            # create postgres database
            await workflow.execute_activity(
                activity=PostgresDatabaseCreationActivity.defn,
                arg=PostgresDatabaseCreationActivityModel(
                    database_name=postgres_database_name,
                ),
                retry_policy=PostgresDatabaseCreationActivity.get_retry_policy(),
                start_to_close_timeout=PostgresDatabaseCreationActivity.get_timeout(),
            )

            # create postgres user for veritable
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

            # secret setup for redis password
            await workflow.execute_activity(
                activity=K8sSecretCreationActivity.defn,
                arg=K8sSecretCreationActivityModel(
                    namespace=tenant,
                    name="tenant-cache-secret",
                    string_data={"REDIS_PASSWORD": redis_tenant_password},
                ),
                retry_policy=K8sSecretCreationActivity.get_retry_policy(),
                start_to_close_timeout=K8sSecretCreationActivity.get_timeout(),
            )

            # secret setup for postgres password
            await workflow.execute_activity(
                activity=K8sSecretCreationActivity.defn,
                arg=K8sSecretCreationActivityModel(
                    namespace=tenant,
                    name="postgres-secret",
                    string_data={"POSTGRES_PASSWORD": postgres_password},
                ),
                retry_policy=K8sSecretCreationActivity.get_retry_policy(),
                start_to_close_timeout=K8sSecretCreationActivity.get_timeout(),
            )

            # setup redis
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

            # kubernetes config map creation
            for config_map in [
                {
                    "name": "veritable-custom-config",
                    "key": "custom-config.json",
                    "template_file_name": "custom-config.tmpl.json",
                },
                {
                    "name": "veritable-env-config",
                    "key": "env-config.json",
                    "template_file_name": f"{config.env}-env-config.tmpl.json",
                },
                {
                    "name": "veritable-tenant-config",
                    "key": "tenant-config.json",
                    "template_file_name": f"{config.env}-tenant-config.tmpl.json",
                },
                {
                    "name": "veritable-cli-vector-config",
                    "key": "vector-config.toml",
                    "template_file_name": "vector-config.tmpl.toml",
                },
                {
                    "name": "veritable-provisioning-config",
                    "key": "provisioning-config.json",
                    "template_file_name": f"{config.env}-provisioning-config.tmpl.json",
                },
            ]:
                await workflow.execute_activity(
                    activity=K8sConfigMapCreationActivity.defn,
                    arg=K8sConfigMapCreationActivityModel(
                        namespace=tenant,
                        name=config_map["name"],
                        template_file_name=config_map["template_file_name"],
                        cloudflare_r2_folder_path="veritable-config",
                        template_payload={
                            "tenant": tenant,
                            "customerId": pydash.get(veritable, "customer_id"),
                            "orgName": pydash.get(veritable, "org_name"),
                        },
                        destination_file_name=config_map["key"],
                    ),
                    retry_policy=K8sConfigMapCreationActivity.get_retry_policy(),
                    start_to_close_timeout=K8sConfigMapCreationActivity.get_timeout(),
                )

            # dns setup
            await workflow.execute_activity(
                activity=CreateCloudflareDNSRecordActivity.defn,
                arg=CreateCloudflareDNSRecordActivityModel(
                    domain_name=f"{tenant}.{veritable_config.domain_name}",
                    zone_id=veritable_config.zone_id,
                ),
                retry_policy=CreateCloudflareDNSRecordActivity.get_retry_policy(),
                start_to_close_timeout=CreateCloudflareDNSRecordActivity.get_timeout(),
            )

            # create bucket
            bucket_name = f"{tenant}.{veritable_config.domain_name}"
            bucket_name = bucket_name.replace(".", "-")
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
                    domain_name=f"{tenant}.{veritable_config.domain_name}",
                    zone_id=veritable_config.zone_id,
                ),
                retry_policy=LinkBucketToDomainActivity.get_retry_policy(),
                start_to_close_timeout=LinkBucketToDomainActivity.get_timeout(),
            )

            # propagate the dns record
            await workflow.execute_activity(
                activity=PropagateDNSRecordActivity.defn,
                arg=PropagateDNSRecordActivityModel(
                    domain_name=f"{tenant}.{veritable_config.domain_name}",
                ),
                retry_policy=PropagateDNSRecordActivity.get_retry_policy(),
                start_to_close_timeout=PropagateDNSRecordActivity.get_timeout(),
            )

            repo_name = "veritable-ui"
            image_tag = "production" if config.env == "production" else "sprint"

            if config.env == "production":
                dest_dir = f"{image_tag}/{bucket_name}"
            else:
                dest_dir = f"/{image_tag}"

            src_object_name = f"{repo_name}/{image_tag}/bundle.zip"

            bundle_path = "bundle/dist"

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

            # keycloak realm setup
            realm_name = f"veritable_{tenant}"
            await workflow.execute_activity(
                activity=KeycloakRealmSetupActivity.defn,
                arg=KeycloakRealmSetupActivityModel(
                    tenant=tenant,
                    domain=veritable_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_realm.json",
                ),
                retry_policy=KeycloakRealmSetupActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakRealmSetupActivity.get_timeout(),
            )

            # keycloak tenant customer admin user setup
            await workflow.execute_activity(
                activity=KeycloakCreateTenantCustomerAdminUserActivity.defn,
                arg=KeycloakCreateTenantCustomerAdminUserActivityModel(
                    realm_name=realm_name,
                    client_name=ProductName,
                    username="admin",
                    email="support@veritable.app",
                    firstname=first_name,
                    lastname=last_name,
                    template_path=TemplatePath,
                    template_name="keycloak_tenant_admin.json",
                ),
                retry_policy=KeycloakCreateTenantCustomerAdminUserActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakCreateTenantCustomerAdminUserActivity.get_timeout(),
            )

            # provisioning job
            await workflow.execute_activity(
                activity=DatabaseMigrationJobActivity.defn,
                arg=DatabaseMigrationJobActivityModel(
                    namespace=tenant,
                    job_name="veritable-tenant-provisioning-job",
                    docker_image=docker_image,
                    volume_mounts=[
                        {
                            "name": "veritable-provisioning-config",
                            "mount_path": "/provisioningConfig",
                            "read_only": True,
                        },
                    ],
                    volumes=[
                        {
                            "name": "veritable-provisioning-config",
                            "config_map_name": "veritable-provisioning-config",
                            "key": "provisioning-config.json",
                            "path": "provisioning-config.json",
                        },
                    ],
                    container_envs=[
                        {"name": "POSTGRES__PASSWORD", "value": postgres_password},
                        {"name": "POSTGRES__USER", "value": postgres_username},
                        {"name": "RELEASE_VERSION", "value": image_tag},
                        {"name": "PROVISIONING_CONFIG", "value": "/provisioningConfig/provisioning-config.json"},
                    ],
                    argument=(
                        "cd /app && python3 /app/provisioning/provisioning_.py "
                        "--config /provisioningConfig/provisioning-config.json"
                    ),
                    job_type="provisioning",
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
                    service_name="veritable",
                    ports={"http": 8000},
                ),
                retry_policy=KubernetesServiceActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesServiceActivity.get_timeout(),
            )

            # kubernetes virtual service
            await workflow.execute_activity(
                activity=KubernetesIstioVirtualServiceActivity.defn,
                arg=KubernetesIstioVirtualServiceActivityModel(
                    namespace=tenant,
                    host=f"{tenant}.{veritable_config.domain_name}",
                    service_name="veritable-vs",
                    payload=http_list,
                ),
                retry_policy=KubernetesIstioVirtualServiceActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesIstioVirtualServiceActivity.get_timeout(),
            )

            # statefulset pod creation for server
            await workflow.execute_activity(
                activity=KubernetesStatefulSetActivity.defn,
                arg=KubernetesStatefulSetActivityModel(
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
                            "mount_path": "/config/custom-config.json",
                            "sub_path": "custom-config.json",
                        },
                        {
                            "name": "env-volume",
                            "mount_path": "/config/env-config.json",
                            "sub_path": "env-config.json",
                        },
                        {
                            "name": "tenant-volume",
                            "mount_path": "/config/tenant-config.json",
                            "sub_path": "tenant-config.json",
                        },
                        {
                            "name": "provisioning-volume",
                            "mount_path": "/config/provisioning-config.json",
                            "sub_path": "provisioning-config.json",
                        },
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "veritable-tenant-config",
                            "key": "tenant-config.json",
                            "path": "tenant-config.json",
                        },
                        {
                            "name": "custom-volume",
                            "config_map_name": "veritable-custom-config",
                            "key": "custom-config.json",
                            "path": "custom-config.json",
                        },
                        {
                            "name": "env-volume",
                            "config_map_name": "veritable-env-config",
                            "key": "env-config.json",
                            "path": "env-config.json",
                        },
                        {
                            "name": "provisioning-volume",
                            "config_map_name": "veritable-provisioning-config",
                            "key": "provisioning-config.json",
                            "path": "provisioning-config.json",
                        },
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "APP_CONFIG_DIR", "value": "/config"},
                        {"name": "POSTGRES__PASSWORD", "value": postgres_password},
                        {"name": "POSTGRES__USER", "value": postgres_username},
                        {"name": "REDIS__HOST", "value": f"cache-new.{tenant}.svc.cluster.local"},
                        {"name": "REDIS__PASSWORD", "value": redis_tenant_password},
                        {"name": "RELEASE_VERSION", "value": image_tag},
                        {"name": "CLIENT_CODE", "value": tenant},
                        {"name": "IS_CLI", "value": "FALSE"},
                        {"name": "ORG_NAME", "value": pydash.get(veritable, "org_name")},
                        {"name": "PROVISIONING_CONFIG", "value": "/config/provisioning-config.json"},
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
                            "mount_path": "/config/custom-config.json",
                            "sub_path": "custom-config.json",
                        },
                        {
                            "name": "env-volume",
                            "mount_path": "/config/env-config.json",
                            "sub_path": "env-config.json",
                        },
                        {
                            "name": "tenant-volume",
                            "mount_path": "/config/tenant-config.json",
                            "sub_path": "tenant-config.json",
                        },
                        {
                            "name": "vector-volume",
                            "mount_path": "/vector",
                            "read_only": True,
                        },
                        {
                            "name": "provisioning-volume",
                            "mount_path": "/config/provisioning-config.json",
                            "sub_path": "provisioning-config.json",
                        },
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "veritable-tenant-config",
                            "key": "tenant-config.json",
                            "path": "tenant-config.json",
                        },
                        {
                            "name": "custom-volume",
                            "config_map_name": "veritable-custom-config",
                            "key": "custom-config.json",
                            "path": "custom-config.json",
                        },
                        {
                            "name": "env-volume",
                            "config_map_name": "veritable-env-config",
                            "key": "env-config.json",
                            "path": "env-config.json",
                        },
                        {
                            "name": "vector-volume",
                            "config_map_name": "veritable-cli-vector-config",
                            "key": "vector-config.toml",
                            "path": "vector-config.toml",
                        },
                        {
                            "name": "provisioning-volume",
                            "config_map_name": "veritable-provisioning-config",
                            "key": "provisioning-config.json",
                            "path": "provisioning-config.json",
                        },
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "APP_CONFIG_DIR", "value": "/config"},
                        {"name": "POSTGRES__PASSWORD", "value": postgres_password},
                        {"name": "POSTGRES__USER", "value": postgres_username},
                        {"name": "REDIS__HOST", "value": f"cache-new.{tenant}.svc.cluster.local"},
                        {"name": "REDIS__PASSWORD", "value": redis_tenant_password},
                        {"name": "RELEASE_VERSION", "value": image_tag},
                        {"name": "CLIENT_CODE", "value": tenant},
                        {"name": "IS_CLI", "value": "TRUE"},
                        {"name": "ORG_NAME", "value": pydash.get(veritable, "org_name")},
                        {"name": "PROVISIONING_CONFIG", "value": "/config/provisioning-config.json"},
                    ],
                ),
                retry_policy=KubernetesStatefulSetActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesStatefulSetActivity.get_timeout(),
            )

            # temporal namespace creation
            await workflow.execute_activity(
                activity=TemporalNamespaceActivity.defn,
                arg=TemporalNamespaceActivityModel(
                    namespace=f"veritable_{tenant}",
                ),
                retry_policy=TemporalNamespaceActivity.get_retry_policy(),
                start_to_close_timeout=TemporalNamespaceActivity.get_timeout(),
            )

            # vm pod scraper for server
            await workflow.execute_activity(
                activity=VMPodScrapperActivity.defn,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="veritable-metrics",
                    app="veritable",
                    path="/metrics/",
                    interval="5s",
                ),
                retry_policy=VMPodScrapperActivity.get_retry_policy(),
                start_to_close_timeout=VMPodScrapperActivity.get_timeout(),
            )

            # vm pod scraper
            await workflow.execute_activity(
                activity=VMPodScrapperActivity.defn,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="veritable-cli-metrics",
                    app="veritable-cli",
                    path="/metrics/",
                    interval="5s",
                ),
                retry_policy=VMPodScrapperActivity.get_retry_policy(),
                start_to_close_timeout=VMPodScrapperActivity.get_timeout(),
            )

            # update tenant status
            await workflow.execute_activity(
                activity=UpdateTenantStatusActivity.defn,
                arg=TenantStatus(
                    tenant_name=tenant,
                    status="Completed",
                    product=ProductName,
                ),
                retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
                start_to_close_timeout=UpdateTenantStatusActivity.get_timeout(),
            )

            # send mail
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
                    domain_name=veritable_config.domain_name,
                    product=ProductName,
                    from_name=veritable_config.sender_name,
                    email_from=veritable_config.sender_email,
                ),
                retry_policy=SendAfterProvisioningMailActivity.get_retry_policy(),
                start_to_close_timeout=SendAfterProvisioningMailActivity.get_timeout(),
            )

            # create tenant crd
            await workflow.execute_activity(
                activity=TenantCrdCreationActivity.defn,
                arg=TenantCrdCreationActivityModel(
                    tenant=tenant,
                    kind="VeritableTenant",
                    product=ProductName,
                    data=orjson.dumps(veritable),
                ),
                retry_policy=TenantCrdCreationActivity.get_retry_policy(),
                start_to_close_timeout=TenantCrdCreationActivity.get_timeout(),
            )

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
        Approve the workflow
        """
        self.approved = True

    @workflow.signal
    async def deny(self: "Workflow") -> None:
        """
        Deny the workflow
        """
        self.deny = True
