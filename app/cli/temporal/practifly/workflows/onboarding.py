from collections.abc import Callable
from temporalio import workflow
import pydash
import orjson
from app.cli.temporal.practifly import TemplatePath
from app.cli.temporal.activities.updateTenantStatus import TenantStatus, UpdateTenantStatusActivity
from app.cli.temporal.activities.temporalNamespace import TemporalNamespaceActivity, TemporalNamespaceActivityModel
from app.cli.temporal.activities.pvcSetup import PVCSetupActivity, PVCSetupActivityModel
from app.cli.temporal.activities.dnsSetup import DnsSetupActivityModel, DnsSetupActivity
from app.cli.temporal.activities.uiSetup import UiSetupActivity, UiSetupActivityModel

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
from app.cli.temporal.activities.keycloakSetup import (
    KeycloakCreateRealmRolesActivity,
    KeycloakCreateRealmRolesActivityModel,
    KeycloakClientSetupActivity,
    KeycloakClientSetupActivityModel,
    KeycloakCreateTenantCustomerAdminUserActivity,
    KeycloakCreateTenantCustomerAdminUserActivityModel,
    KeycloakRealmSetupActivity,
    KeycloakRealmSetupActivityModel,
)
from app.cli.temporal.activities.statefulSetPodCreation import (
    KubernetesStatefulSetActivity,
    KubernetesStatefulSetActivityModel,
)
from app.cli.temporal.activities.sendMail import (
    SendAfterProvisioningMailActivity,
    SendAfterProvisioningMailActivityModel,
    SendBeforeProvisioningMailActivity,
    SendBeforeProvisioningMailActivityModel,
)
from app.cli.temporal.core.base import Workflow
from app.cli.temporal.practifly.models.practiflySpec import PractiflySpec
from app.cli.temporal.activities.k8sSecret import K8sSecretCreationActivity, K8sSecretCreationActivityModel
from app.cli.temporal.activities.k8sService import KubernetesServiceActivity, KubernetesServiceActivityModel
from app.cli.temporal.activities.k8sconfigMap import K8sConfigMapCreationActivity, K8sConfigMapCreationActivityModel
from app.cli.temporal.activities.vmPodScrapper import VMPodScrapperActivity, VMPodScrapperActivityModel
from app.cli.temporal.activities.redis import RedisSetupActivity, RedisSetupActivityModel
from app.cli.temporal.activities.k8sIstioVirtualService import (
    KubernetesIstioVirtualServiceActivity,
    KubernetesIstioVirtualServiceActivityModel,
)
from app.cli.temporal.activities.databaseMigrationJob import (
    DatabaseMigrationJobActivity,
    DatabaseMigrationJobActivityModel,
)

with workflow.unsafe.imports_passed_through():
    from app.common import generate_password
    from app.core.settings import AppSettings, PractiflySettings, get_settings
    from app.template_env import get_env


ProductName = "practifly"
OnePasswordVaultName = "practifly"


@workflow.defn(name="PractiflyOnboardingWorkflow", sandboxed=False)
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
            SendAfterProvisioningMailActivity.defn,
            UpdateTenantStatusActivity.defn,
            PostgresDatabaseCreationActivity.defn,
            PostgresUserCreationActivity.defn,
            PostgresSupavisorPollUserActivity.defn,
            PostgresSchemaCreationActivity.defn,
            PostgresGrantAccessToUserActivity.defn,
            KeycloakRealmSetupActivity.defn,
            KeycloakClientSetupActivity.defn,
            KeycloakCreateRealmRolesActivity.defn,
            KeycloakCreateTenantCustomerAdminUserActivity.defn,
            VMPodScrapperActivity.defn,
            PVCSetupActivity.defn,
            TemporalNamespaceActivity.defn,
            K8sSecretCreationActivity.defn,
            KubernetesServiceActivity.defn,
            KubernetesIstioVirtualServiceActivity.defn,
            RedisSetupActivity.defn,
            K8sConfigMapCreationActivity.defn,
            DnsSetupActivity.defn,
            UiSetupActivity.defn,
            DatabaseMigrationJobActivity.defn,
        ]

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
            postgres_database_name = ProductName
            postgres_username = f"{ProductName}_{tenant}"
            postgres_password = generate_password(length=20)
            template_env = get_env(template_path=TemplatePath)
            image_tag = "production" if config.env == "production" else "sprint"
            docker_image = f"registry.314ecorp.tech/practifly-app:{image_tag}"
            template = template_env.get_template("istio-rules.json")
            output = template.render(tenant=tenant, image_tag=image_tag)

            http_list = orjson.loads(output)

            # temporal namespace creation
            await workflow.execute_activity(
                activity=TemporalNamespaceActivity.defn,
                arg=TemporalNamespaceActivityModel(
                    namespace=f"{ProductName}_{tenant}",
                ),
                retry_policy=TemporalNamespaceActivity.get_retry_policy(),
                start_to_close_timeout=TemporalNamespaceActivity.get_timeout(),
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

            # kubernetes service
            await workflow.execute_activity(
                activity=KubernetesServiceActivity.defn,
                arg=KubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="practifly",
                    port=8000,
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

            for config_map in [
                {"name": "practifly-common-config", "key": "common-config.json"},
                {"name": "practifly-env-config", "key": "env-config.json"},
                {"name": "practifly-tenant-config", "key": "tenant-config.json"},
                {"name": "practifly-cli-vector-config", "key": "vector-config.toml"},
                {"name": "practifly-provisioning-config", "key": "provisioning-config.json"},
            ]:
                await workflow.execute_activity(
                    activity=K8sConfigMapCreationActivity.defn,
                    arg=K8sConfigMapCreationActivityModel(
                        namespace=tenant,
                        name=config_map["name"],
                        template_file_name=config_map["key"],
                        cloudflare_r2_folder_path="practifly-config",
                        template_payload={"tenant": tenant},
                    ),
                    retry_policy=K8sConfigMapCreationActivity.get_retry_policy(),
                    start_to_close_timeout=K8sConfigMapCreationActivity.get_timeout(),
                )

            # dns setup
            await workflow.execute_activity(
                activity=DnsSetupActivity.defn,
                arg=DnsSetupActivityModel(
                    cname=config.k8s_cname,
                    fqdn=f"{tenant}.api.{practifly_config.domain_name}.",
                    zone_name=practifly_config.zone_name,
                ),
                retry_policy=DnsSetupActivity.get_retry_policy(),
                start_to_close_timeout=DnsSetupActivity.get_timeout(),
            )

            # ui setup
            repo_name = "practifly-ui"
            image_tag = "production" if config.env == "production" else "sprint"

            if config.env == "production":
                dest_dir = f"{tenant}.api.{practifly_config.domain_name}/"
            else:
                dest_dir = f"{tenant}.api.{practifly_config.domain_name}/{image_tag}"

            src_object_name = f"{repo_name}/{image_tag}/bundle.zip"

            bundle_path = "bundle/dist/admin"

            await workflow.execute_activity(
                activity=UiSetupActivity.defn,
                arg=UiSetupActivityModel(
                    src_object_name=src_object_name,
                    dest_dir=dest_dir,
                    bundle_path=bundle_path,
                    bundle_name="bundle.zip",
                ),
                retry_policy=UiSetupActivity.get_retry_policy(),
                start_to_close_timeout=UiSetupActivity.get_timeout(),
            )

            # atlas job
            await workflow.execute_activity(
                activity=DatabaseMigrationJobActivity.defn,
                arg=DatabaseMigrationJobActivityModel(
                    namespace=tenant,
                    job_name="practifly-atlas-migration-job",
                    docker_image=docker_image,
                    volume_mounts=[
                        {
                            "name": "common-volume",
                            "mount_path": "/config/common-config.json",
                            "sub_path": "common-config.json",
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
                        {
                            "name": "vector-volume",
                            "mount_path": "/config/vector-config.toml",
                            "sub_path": "vector-config.toml",
                        },
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "practifly-tenant-config",
                            "key": "tenant-config.json",
                            "path": "tenant-config.json",
                        },
                        {
                            "name": "common-volume",
                            "config_map_name": "practifly-common-config",
                            "key": "common-config.json",
                            "path": "common-config.json",
                        },
                        {
                            "name": "env-volume",
                            "config_map_name": "practifly-env-config",
                            "key": "env-config.json",
                            "path": "env-config.json",
                        },
                        {
                            "name": "provisioning-volume",
                            "config_map_name": "practifly-provisioning-config",
                            "key": "provisioning-config.json",
                            "path": "provisioning-config.json",
                        },
                        {
                            "name": "vector-volume",
                            "config_map_name": "practifly-cli-vector-config",
                            "key": "vector-config.toml",
                            "path": "vector-config.toml",
                        },
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "APP_CONFIG_DIR", "value": "/config"},
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

            # keycloak realm setup
            realm_name = tenant
            await workflow.execute_activity(
                activity=KeycloakRealmSetupActivity.defn,
                arg=KeycloakRealmSetupActivityModel(
                    tenant=tenant,
                    domain=practifly_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_realm.json",
                ),
                retry_policy=KeycloakRealmSetupActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakRealmSetupActivity.get_timeout(),
            )

            ## TODO: check if this is needed
            # keycloak client setup
            await workflow.execute_activity(
                activity=KeycloakClientSetupActivity.defn,
                arg=KeycloakClientSetupActivityModel(
                    tenant=tenant,
                    realm_name=realm_name,
                    domain=practifly_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_practifly_client.json",
                ),
                retry_policy=KeycloakClientSetupActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakClientSetupActivity.get_timeout(),
            )

            # keycloak tenant customer admin user setup
            await workflow.execute_activity(
                activity=KeycloakCreateTenantCustomerAdminUserActivity.defn,
                arg=KeycloakCreateTenantCustomerAdminUserActivityModel(
                    realm_name=realm_name,
                    client_name=ProductName,
                    username="admin",
                    email="practifly-be@314ecorp.com",
                    firstname=first_name,
                    lastname=last_name,
                    template_path=TemplatePath,
                    template_name="keycloak_tenant_admin.json",
                ),
                retry_policy=KeycloakCreateTenantCustomerAdminUserActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakCreateTenantCustomerAdminUserActivity.get_timeout(),
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
                    container_ports=[8000],
                    volume_mounts=[
                        {
                            "name": "common-volume",
                            "mount_path": "/config/common-config.json",
                            "sub_path": "common-config.json",
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
                        {
                            "name": "vector-volume",
                            "mount_path": "/config/vector-config.toml",
                            "sub_path": "vector-config.toml",
                        },
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "practifly-tenant-config",
                            "key": "tenant-config.json",
                            "path": "tenant-config.json",
                        },
                        {
                            "name": "common-volume",
                            "config_map_name": "practifly-common-config",
                            "key": "common-config.json",
                            "path": "common-config.json",
                        },
                        {
                            "name": "env-volume",
                            "config_map_name": "practifly-env-config",
                            "key": "env-config.json",
                            "path": "env-config.json",
                        },
                        {
                            "name": "provisioning-volume",
                            "config_map_name": "practifly-provisioning-config",
                            "key": "provisioning-config.json",
                            "path": "provisioning-config.json",
                        },
                        {
                            "name": "vector-volume",
                            "config_map_name": "practifly-cli-vector-config",
                            "key": "vector-config.toml",
                            "path": "vector-config.toml",
                        },
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "APP_CONFIG_DIR", "value": "/config"},
                        {"name": "POSTGRES_PASSWORD", "value": postgres_password},
                        {"name": "POSTGRES_USER", "value": postgres_username},
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
                    name="practifly-worker",
                    docker_image=docker_image,
                    request_resource={
                        "cpu": pydash.get(practifly, "cliSpec.request_cpu"),
                        "memory": pydash.get(practifly, "cliSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(practifly, "cliSpec.limit_cpu"),
                        "memory": pydash.get(practifly, "cliSpec.limit_memory"),
                    },
                    container_ports=[8000],
                    volume_mounts=[
                        {
                            "name": "common-volume",
                            "mount_path": "/config/common-config.json",
                            "sub_path": "common-config.json",
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
                        {
                            "name": "vector-volume",
                            "mount_path": "/config/vector-config.toml",
                            "sub_path": "vector-config.toml",
                        },
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "practifly-tenant-config",
                            "key": "tenant-config.json",
                            "path": "tenant-config.json",
                        },
                        {
                            "name": "common-volume",
                            "config_map_name": "practifly-common-config",
                            "key": "common-config.json",
                            "path": "common-config.json",
                        },
                        {
                            "name": "env-volume",
                            "config_map_name": "practifly-env-config",
                            "key": "env-config.json",
                            "path": "env-config.json",
                        },
                        {
                            "name": "provisioning-volume",
                            "config_map_name": "practifly-provisioning-config",
                            "key": "provisioning-config.json",
                            "path": "provisioning-config.json",
                        },
                        {
                            "name": "vector-volume",
                            "config_map_name": "practifly-cli-vector-config",
                            "key": "vector-config.toml",
                            "path": "vector-config.toml",
                        },
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "APP_CONFIG_DIR", "value": "/config"},
                        {"name": "POSTGRES_PASSWORD", "value": postgres_password},
                        {"name": "POSTGRES_USER", "value": postgres_username},
                    ],
                ),
                retry_policy=KubernetesStatefulSetActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesStatefulSetActivity.get_timeout(),
            )

            # vm pod scraper
            await workflow.execute_activity(
                activity=VMPodScrapperActivity.defn,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="practifly-metrics",
                    app=ProductName,
                    path="/metrics/",
                    interval="15s",
                ),
                retry_policy=VMPodScrapperActivity.get_retry_policy(),
                start_to_close_timeout=VMPodScrapperActivity.get_timeout(),
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
                    domain_name=practifly_config.domain_name,
                    product=ProductName,
                    from_name=practifly_config.sender_name,
                    email_from=practifly_config.sender_email,
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
