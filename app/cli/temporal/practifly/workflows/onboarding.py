from collections.abc import Callable

import orjson
import pydash
from cryptography.fernet import Fernet
from temporalio import workflow

from app.cli.temporal.activities.cloudflareSetup import (
    CopyArtifactsToBucketActivity,
    CopyArtifactsToBucketActivityModel,
    CopyWebCoreToBucketActivity,
    CopyWebCoreToBucketActivityModel,
    CreateCloudflareBucketActivity,
    CreateCloudflareBucketActivityModel,
    CreateCloudflareDNSRecordActivity,
    CreateCloudflareDNSRecordActivityModel,
    LinkBucketToDomainActivity,
    LinkBucketToDomainActivityModel,
    PropagateDNSRecordActivity,
    PropagateDNSRecordActivityModel,
)
from app.cli.temporal.activities.k8sconfigMap import K8sConfigMapCreationActivity, K8sConfigMapCreationActivityModel
from app.cli.temporal.activities.k8sIstioVirtualService import (
    KubernetesIstioVirtualServiceActivity,
    KubernetesIstioVirtualServiceActivityModel,
)
from app.cli.temporal.activities.k8snamespace import K8sNamespaceCreationActivity, K8sNamespaceCreationActivityModel
from app.cli.temporal.activities.k8sSecret import K8sSecretCreationActivity, K8sSecretCreationActivityModel
from app.cli.temporal.activities.k8sService import KubernetesServiceActivity, KubernetesServiceActivityModel
from app.cli.temporal.activities.keycloakSetup import (
    KeycloakCreateInternalUsersActivity,
    KeycloakCreateInternalUsersActivityModel,
    KeycloakCreateTenantCustomerAdminUserActivity,
    KeycloakCreateTenantCustomerAdminUserActivityModel,
    KeycloakRealmSetupActivity,
    KeycloakRealmSetupActivityModel,
)
from app.cli.temporal.activities.onePassword import (
    OnePasswordInsertIfNotExistsActivity,
    OnePasswordInsertIfNotExistsActivityModel,
)
from app.cli.temporal.activities.postgresSetup import (
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
from app.cli.temporal.activities.practiflyJob import (
    PractiflyJobActivity,
    PractiflyJobActivityModel,
)
from app.cli.temporal.activities.pvcSetup import PVCSetupActivity, PVCSetupActivityModel
from app.cli.temporal.activities.redis import RedisSetupFromSecretActivity, RedisSetupFromSecretActivityModel
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
from app.cli.temporal.activities.tenantCrd import (
    TenantCrdCreationActivity,
    TenantCrdCreationActivityModel,
    TenantCrdExistsActivity,
    TenantCrdExistsActivityModel,
)
from app.cli.temporal.activities.updateTenantStatus import TenantStatus, UpdateTenantStatusActivity
from app.cli.temporal.activities.vmPodScrapper import VMPodScrapperActivity, VMPodScrapperActivityModel
from app.cli.temporal.core.base import Workflow
from app.cli.temporal.practifly import TemplatePath
from app.cli.temporal.practifly.models.practiflySpec import PractiflyJobEnum, PractiflySpec
from app.common import generate_password
from app.core.settings import AppSettings, PractiflySettings, get_settings
from app.template_env import get_env

ProductName = "practifly"
OnePasswordVaultName = "practifly"


@workflow.defn(sandboxed=False)
class PractiflyOnboardingWorkflow(Workflow):
    """
    Practifly Onboarding Workflow
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
            KubernetesStatefulSetActivity.defn,
            UpdateTenantStatusActivity.defn,
            SendAfterProvisioningMailActivity.defn,
            TenantCrdExistsActivity.defn,
            TenantCrdCreationActivity.defn,
            KeycloakCreateInternalUsersActivity.defn,
            CheckPodRunningStatusActivity.defn,
            OnePasswordInsertIfNotExistsActivity.defn,
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

        try:
            # get tenant crd
            tenant_crd_exists: bool = await workflow.execute_activity(
                activity=TenantCrdExistsActivity.defn,
                arg=TenantCrdExistsActivityModel(
                    tenant=tenant,
                    kind="PractiflyTenant",
                    product=ProductName,
                ),
                retry_policy=TenantCrdExistsActivity.get_retry_policy(),
                start_to_close_timeout=TenantCrdExistsActivity.get_timeout(),
            )

            if tenant_crd_exists:
                raise ValueError(f"Tenant {tenant} already exists")  # noqa: TRY301

            if not pydash.get(practifly, "emailSent"):
                await workflow.execute_activity(
                    activity=SendBeforeProvisioningMailActivity.defn,
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
            postgres_secret_name = f"{ProductName}-postgres"

            redis_tenant_password = generate_password(length=20)
            redis_secret_name = f"{ProductName}-redis"

            template_env = get_env(template_path=TemplatePath)
            image_tag = "production" if config.env == "production" else "sprint"
            docker_image = f"registry.314ecorp.tech/practifly-server:{image_tag}"
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

            # kubernetes namespace creation
            await workflow.execute_activity(
                activity=K8sNamespaceCreationActivity.defn,
                arg=K8sNamespaceCreationActivityModel(
                    namespace=tenant,
                ),
                retry_policy=K8sNamespaceCreationActivity.get_retry_policy(),
                start_to_close_timeout=K8sNamespaceCreationActivity.get_timeout(),
            )

            # secret setup for redis password
            await workflow.execute_activity(
                activity=K8sSecretCreationActivity.defn,
                arg=K8sSecretCreationActivityModel(
                    namespace=tenant,
                    name=redis_secret_name,
                    string_data={"password": redis_tenant_password},
                ),
                retry_policy=K8sSecretCreationActivity.get_retry_policy(),
                start_to_close_timeout=K8sSecretCreationActivity.get_timeout(),
            )

            # secret setup for postgres password
            await workflow.execute_activity(
                activity=K8sSecretCreationActivity.defn,
                arg=K8sSecretCreationActivityModel(
                    namespace=tenant,
                    name=postgres_secret_name,
                    string_data={"password": postgres_password},
                ),
                retry_policy=K8sSecretCreationActivity.get_retry_policy(),
                start_to_close_timeout=K8sSecretCreationActivity.get_timeout(),
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

            # create postgres user for practifly
            await workflow.execute_activity(
                activity=PostgresUserCreationFromSecretActivity.defn,
                arg=PostgresUserCreationFromSecretActivityModel(
                    username=postgres_username,
                    database_name=postgres_database_name,
                    secret_name=postgres_secret_name,
                    namespace=tenant,
                ),
                retry_policy=PostgresUserCreationFromSecretActivity.get_retry_policy(),
                start_to_close_timeout=PostgresUserCreationFromSecretActivity.get_timeout(),
            )

            # create postgres user in supavisor for practifly
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

            # create postgres schema
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

            # grant access to postgres user
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

            # secret setup for redis master password
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

            # setup redis
            await workflow.execute_activity(
                activity=RedisSetupFromSecretActivity.defn,
                arg=RedisSetupFromSecretActivityModel(
                    namespace=tenant,
                    product=ProductName,
                    secret_name=redis_secret_name,
                ),
                retry_policy=RedisSetupFromSecretActivity.get_retry_policy(),
                start_to_close_timeout=RedisSetupFromSecretActivity.get_timeout(),
            )

            # pvc setup
            await workflow.execute_activity(
                activity=PVCSetupActivity.defn,
                arg=PVCSetupActivityModel(
                    tenant=tenant,
                    pvc_name="practifly-pvc",
                ),
                retry_policy=PVCSetupActivity.get_retry_policy(),
                start_to_close_timeout=PVCSetupActivity.get_timeout(),
            )

            # kubernetes service
            await workflow.execute_activity(
                activity=KubernetesServiceActivity.defn,
                arg=KubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="practifly",
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
                    host=f"{tenant}.api.{practifly_config.domain_name}",
                    service_name="practifly-vs",
                    payload=http_list,
                ),
                retry_policy=KubernetesIstioVirtualServiceActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesIstioVirtualServiceActivity.get_timeout(),
            )
            # insert fernet key into 1Password if it doesn't exist
            fernet_key = Fernet.generate_key().decode()
            await workflow.execute_activity(
                activity=OnePasswordInsertIfNotExistsActivity.defn,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=tenant,
                    vault=OnePasswordVaultName,
                    server_item=f"practifly-tenant-config-{config.env.lower().strip()}",
                    key="fernet_key",
                    key_value=fernet_key,
                ),
                retry_policy=OnePasswordInsertIfNotExistsActivity.get_retry_policy(),
                start_to_close_timeout=OnePasswordInsertIfNotExistsActivity.get_timeout(),
            )

            common_config = "common-config.json"
            env_config = f"{config.env}-env-config.json"
            tenant_config = "tenant-config.json"
            vector_config = "vector-config.toml"
            provisioning_config = f"{config.env}-provisioning-config.json"
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
                await workflow.execute_activity(
                    activity=K8sConfigMapCreationActivity.defn,
                    arg=K8sConfigMapCreationActivityModel(
                        namespace=tenant,
                        name=config_map["name"],
                        template_file_name=config_map["template_file_name"],
                        cloudflare_r2_folder_path="practifly-config",
                        template_payload={"tenant": tenant},
                        destination_file_name=config_map["key"],
                    ),
                    retry_policy=K8sConfigMapCreationActivity.get_retry_policy(),
                    start_to_close_timeout=K8sConfigMapCreationActivity.get_timeout(),
                )

            # dns setup
            await workflow.execute_activity(
                activity=CreateCloudflareDNSRecordActivity.defn,
                arg=CreateCloudflareDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{practifly_config.domain_name}",
                    zone_id=practifly_config.zone_id,
                    content=config.k8s_cname,
                ),
                retry_policy=CreateCloudflareDNSRecordActivity.get_retry_policy(),
                start_to_close_timeout=CreateCloudflareDNSRecordActivity.get_timeout(),
            )

            # create bucket
            bucket_name = f"{tenant}.{practifly_config.domain_name}"
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
                    domain_name=f"{tenant}.{practifly_config.domain_name}",
                    zone_id=practifly_config.zone_id,
                ),
                retry_policy=LinkBucketToDomainActivity.get_retry_policy(),
                start_to_close_timeout=LinkBucketToDomainActivity.get_timeout(),
            )

            # propagate the dns record
            await workflow.execute_activity(
                activity=PropagateDNSRecordActivity.defn,
                arg=PropagateDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{practifly_config.domain_name}",
                ),
                retry_policy=PropagateDNSRecordActivity.get_retry_policy(),
                start_to_close_timeout=PropagateDNSRecordActivity.get_timeout(),
            )

            # keycloak realm setup
            realm_name = f"{tenant}"
            await workflow.execute_activity(
                activity=KeycloakRealmSetupActivity.defn,
                arg=KeycloakRealmSetupActivityModel(
                    realm_name=realm_name,
                    domain=practifly_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_realm.json",
                ),
                retry_policy=KeycloakRealmSetupActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakRealmSetupActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=KeycloakCreateTenantCustomerAdminUserActivity.defn,
                arg=KeycloakCreateTenantCustomerAdminUserActivityModel(
                    realm_name=f"practifly_{tenant}",
                    username=email,
                    email=email,
                    firstname=first_name,
                    lastname=last_name,
                    template_path=TemplatePath,
                    template_name="keycloak_customer_admin.json",
                ),
                retry_policy=KeycloakCreateTenantCustomerAdminUserActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakCreateTenantCustomerAdminUserActivity.get_timeout(),
            )

            # keycloak tenant internal admin user setup
            await workflow.execute_activity(
                activity=KeycloakCreateInternalUsersActivity.defn,
                arg=KeycloakCreateInternalUsersActivityModel(
                    realm_name=f"practifly_{tenant}",
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
                retry_policy=KeycloakCreateInternalUsersActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakCreateInternalUsersActivity.get_timeout(),
            )

            # temporal namespace creation
            await workflow.execute_activity(
                activity=TemporalNamespaceActivity.defn,
                arg=TemporalNamespaceActivityModel(
                    namespace=f"practifly_{tenant}",
                ),
                retry_policy=TemporalNamespaceActivity.get_retry_policy(),
                start_to_close_timeout=TemporalNamespaceActivity.get_timeout(),
            )

            # vm pod scraper for server
            await workflow.execute_activity(
                activity=VMPodScrapperActivity.defn,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="practifly-metrics",
                    app="practifly",
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
                    name="practifly-cli-metrics",
                    app="practifly-cli",
                    path="/metrics/",
                    interval="5s",
                ),
                retry_policy=VMPodScrapperActivity.get_retry_policy(),
                start_to_close_timeout=VMPodScrapperActivity.get_timeout(),
            )

            # alembic job
            await workflow.execute_activity(
                activity=PractiflyJobActivity.defn,
                arg=PractiflyJobActivityModel(
                    tenant=tenant,
                    image_tag=image_tag,
                    job_type=PractiflyJobEnum.PROVISIONING,
                ),
                retry_policy=PractiflyJobActivity.get_retry_policy(),
                start_to_close_timeout=PractiflyJobActivity.get_timeout(),
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

            src_object_name = f"practifly-web-core/{image_tag}/release.zip"
            web_core_bucket_name = "practifly-web-core"
            dest_dir = f"{web_core_bucket_name}/{bucket_name}"

            # copy webcore to bucket
            await workflow.execute_activity(
                activity=CopyWebCoreToBucketActivity.defn,
                arg=CopyWebCoreToBucketActivityModel(
                    src_object_name=src_object_name,
                    tenant=tenant,
                    bucket_name=web_core_bucket_name,
                    bundle_name="release.zip",
                    dest_dir=dest_dir,
                ),
                retry_policy=CopyWebCoreToBucketActivity.get_retry_policy(),
                start_to_close_timeout=CopyWebCoreToBucketActivity.get_timeout(),
            )

            # statefulset pod creation for server
            await workflow.execute_activity(
                activity=KubernetesStatefulSetActivity.defn,
                arg=KubernetesStatefulSetActivityModel(
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
                            "value_from": {
                                "secret_name": {"name": postgres_secret_name, "key": "password"},
                            },
                        },
                        {"name": "POSTGRES__USER", "value": postgres_username},
                        {"name": "REDIS__HOST", "value": f"cache-new.{tenant}.svc.cluster.local"},
                        {
                            "name": "REDIS__PASSWORD",
                            "value_from": {
                                "secret_name": {"name": redis_secret_name, "key": "password"},
                            },
                        },
                        {"name": "RELEASE_VERSION", "value": image_tag},
                        {"name": "CLIENT_CODE", "value": tenant},
                        {"name": "IS_CLI", "value": "FALSE"},
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
                            "value_from": {
                                "secret_name": {"name": postgres_secret_name, "key": "password"},
                            },
                        },
                        {"name": "POSTGRES__USER", "value": postgres_username},
                        {"name": "REDIS__HOST", "value": f"cache-new.{tenant}.svc.cluster.local"},
                        {
                            "name": "REDIS__PASSWORD",
                            "value_from": {
                                "secret_name": {"name": redis_secret_name, "key": "password"},
                            },
                        },
                        {"name": "RELEASE_VERSION", "value": image_tag},
                        {"name": "CLIENT_CODE", "value": tenant},
                        {"name": "IS_CLI", "value": "TRUE"},
                    ],
                ),
                retry_policy=KubernetesStatefulSetActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesStatefulSetActivity.get_timeout(),
            )

            # check pod running status
            for pod in ["practifly", "practifly-cli"]:
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
            await workflow.execute_activity(
                activity=SendAfterProvisioningMailActivity.defn,
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
                retry_policy=SendAfterProvisioningMailActivity.get_retry_policy(),
                start_to_close_timeout=SendAfterProvisioningMailActivity.get_timeout(),
            )

            # create tenant crd
            await workflow.execute_activity(
                activity=TenantCrdCreationActivity.defn,
                arg=TenantCrdCreationActivityModel(
                    tenant=tenant,
                    kind="PractiflyTenant",
                    product=ProductName,
                    data=orjson.dumps(practifly),
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
