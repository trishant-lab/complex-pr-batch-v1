from collections.abc import Callable
from datetime import timedelta

import orjson
import pydash
from temporalio import workflow

from app.cli.temporal.activities.databaseMigrationJob import (
    DatabaseMigrationJobActivity,
    DatabaseMigrationJobActivityModel,
)
from app.cli.temporal.activities.dexitNovuSetup import DexitNovuSetupActivity
from app.cli.temporal.activities.dnsSetup import DnsSetupActivityModel, DnsSetupActivity
from app.cli.temporal.activities.faxSetup import FaxSetupActivity
from app.cli.temporal.activities.hfinferenceendpoint import HFInferenceEndpointSetupActivity
from app.cli.temporal.activities.k8sIstioVirtualService import (
    KubernetesIstioVirtualServiceActivity,
    KubernetesIstioVirtualServiceActivityModel,
)
from app.cli.temporal.activities.k8sSecret import K8sSecretCreationActivity, K8sSecretCreationActivityModel
from app.cli.temporal.activities.k8sService import KubernetesServiceActivity, KubernetesServiceActivityModel
from app.cli.temporal.activities.k8sconfigMap import K8sConfigMapCreationActivity, K8sConfigMapCreationActivityModel
from app.cli.temporal.activities.k8snamespace import K8sNamespaceCreationActivity, K8sNamespaceCreationActivityModel
from app.cli.temporal.activities.keycloakSetup import (
    KeycloakRealmSetupActivity,
    KeycloakRealmSetupActivityModel,
    KeycloakClientSetupActivity,
    KeycloakClientSetupActivityModel,
    KeycloakCreateClientRolesActivity,
    KeycloakCreateClientRolesActivityModel,
    KeycloakCreateTenantCustomerAdminUserActivity,
    KeycloakCreateTenantCustomerAdminUserActivityModel,
    KeycloakServiceAccountSetupActivity,
    KeycloakServiceAccountSetupActivityModel,
)
from app.cli.temporal.activities.onePassword import (
    OnePasswordCreateOrUpdateActivity,
    OnePasswordCreateOrUpdateActivityModel,
)
from app.cli.temporal.activities.postgresSetup import (
    PostgresUserCreationActivity,
    PostgresUserCreationActivityModel,
    PostgresSchemaCreationActivity,
    PostgresSchemaCreationActivityModel,
    PostgresGrantAccessToUserActivity,
    PostgresGrantAccessToUserActivityModel,
    KeycloakUserMappingActivity,
    KeycloakUserMappingActivityModel,
    MatomoUserMappingActivity,
    MatomoUserMappingActivityModel,
    PostgresGrantAllPrivilegesOnTableActivity,
    PostgresGrantAllPrivilegesOnTableActivityModel,
    PostgresDatabaseCreationActivity,
    PostgresDatabaseCreationActivityModel,
)
from app.cli.temporal.activities.sendMail import (
    SendAfterProvisioningMailActivity,
    SendAfterProvisioningMailActivityModel,
)
from app.cli.temporal.activities.statefulSetPodCreation import (
    KubernetesStatefulSetActivity,
    KubernetesStatefulSetActivityModel,
)
from app.cli.temporal.activities.temporalNamespace import TemporalNamespaceActivity, TemporalNamespaceActivityModel
from app.cli.temporal.activities.temporalSearchAtrributesCreation import (
    TemporalSearchAttributesCreationActivity,
    TemporalSearchAttributesCreationActivityModel,
)
from app.cli.temporal.activities.uiSetup import UiSetupActivity, UiSetupActivityModel
from app.cli.temporal.activities.updateTenantStatus import UpdateTenantStatusActivity, TenantStatus
from app.cli.temporal.activities.vmPodScrapper import VMPodScrapperActivity, VMPodScrapperActivityModel
from app.cli.temporal.dexit import TemplatePath
from app.cli.temporal.dexit.models.dexitSpec import DexitSpec
from app.cli.temporal.core.base import Workflow
from app.common import generate_password
from app.core.settings import AppSettings, get_settings, DexitSettings
from app.template_env import get_env

ProductName = "dexit"
OnePasswordVaultName = "Dexit"


@workflow.defn(name="DexitOnboardingWorkflow", sandboxed=False)
class DexitOnboardingWorkflow(Workflow):
    """
    Dexit Onboarding Workflow
    """

    def __init__(self: "Workflow") -> None:
        self.approved: bool = False
        self.deny: bool = False

    @staticmethod
    def get_activities() -> list[type[Callable]]:
        """
        Return list of activities used in the workflow
        """
        return [
            SendAfterProvisioningMailActivity.defn,
            UpdateTenantStatusActivity.defn,
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
            DnsSetupActivity.defn,
            UiSetupActivity.defn,
            KeycloakRealmSetupActivity.defn,
            KeycloakClientSetupActivity.defn,
            KeycloakCreateClientRolesActivity.defn,
            KeycloakCreateTenantCustomerAdminUserActivity.defn,
            KubernetesStatefulSetActivity.defn,
            VMPodScrapperActivity.defn,
            KubernetesIstioVirtualServiceActivity.defn,
            KubernetesServiceActivity.defn,
            K8sConfigMapCreationActivity.defn,
            TemporalNamespaceActivity.defn,
            TemporalSearchAttributesCreationActivity.defn,
            FaxSetupActivity.defn,
            HFInferenceEndpointSetupActivity.defn,
            OnePasswordCreateOrUpdateActivity.defn,
            PostgresDatabaseCreationActivity.defn,
            KeycloakServiceAccountSetupActivity.defn,
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
            await workflow.wait_condition(lambda: self.approved or self.deny)

            if self.deny:
                await workflow.execute_activity(
                    activity=UpdateTenantStatusActivity.defn,
                    arg=TenantStatus(
                        tenant_name=pydash.get(dexit, "tenant"),
                        status="Declined",
                        error_msg="Request Declined",
                        product=ProductName,
                    ),
                    retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
                    start_to_close_timeout=timedelta(seconds=120),
                )
                return

            postgres_schema_name = tenant
            postgres_database_name = "dexit"
            postgres_username = f"{ProductName}_{tenant}"
            postgres_password = generate_password(length=20)
            dicom_database_name = f"{ProductName}_dicom_{tenant}"
            dicom_database_password = generate_password(length=20)
            image_tag = "production" if config.env == "production" else "sprint"
            docker_image = f"registry.314ecorp.tech/dexit-app:{image_tag}"
            server_item = "production-config" if config.env == "production" else "integration-config"

            await workflow.execute_activity(
                activity=OnePasswordCreateOrUpdateActivity.defn,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=tenant,
                    server_item=server_item,
                    vault=OnePasswordVaultName,
                    secret_name="pg_dicom_password",
                    secret_value=dicom_database_password,
                ),
                retry_policy=OnePasswordCreateOrUpdateActivity.get_retry_policy(),
                start_to_close_timeout=OnePasswordCreateOrUpdateActivity.get_timeout(),
            )

            # create postgres database for dicom
            await workflow.execute_activity(
                activity=PostgresDatabaseCreationActivity.defn,
                arg=PostgresDatabaseCreationActivityModel(
                    database_name=dicom_database_name,
                ),
                retry_policy=PostgresDatabaseCreationActivity.get_retry_policy(),
                start_to_close_timeout=PostgresDatabaseCreationActivity.get_timeout(),
            )

            # create postgres user for dicom
            await workflow.execute_activity(
                activity=PostgresUserCreationActivity.defn,
                arg=PostgresUserCreationActivityModel(
                    username=dicom_database_name,
                    database_name=dicom_database_name,
                    password=dicom_database_password,
                ),
                retry_policy=PostgresUserCreationActivity.get_retry_policy(),
                start_to_close_timeout=PostgresUserCreationActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=PostgresGrantAccessToUserActivity.defn,
                arg=PostgresGrantAccessToUserActivityModel(
                    username=dicom_database_name,
                    database_name=dicom_database_name,
                ),
                retry_policy=PostgresGrantAccessToUserActivity.get_retry_policy(),
                start_to_close_timeout=PostgresGrantAccessToUserActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=OnePasswordCreateOrUpdateActivity.defn,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=tenant,
                    server_item=server_item,
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

            # setup novu
            await workflow.execute_activity(
                activity=DexitNovuSetupActivity.defn,
                arg=dexit,
                retry_policy=DexitNovuSetupActivity.get_retry_policy(),
                start_to_close_timeout=DexitNovuSetupActivity.get_timeout(),
            )

            # fax setup
            await workflow.execute_activity(
                activity=FaxSetupActivity.defn,
                arg=dexit,
                retry_policy=FaxSetupActivity.get_retry_policy(),
                start_to_close_timeout=FaxSetupActivity.get_timeout(),
            )

            realm_name = tenant
            # keycloak realm setup
            await workflow.execute_activity(
                activity=KeycloakRealmSetupActivity.defn,
                arg=KeycloakRealmSetupActivityModel(
                    tenant=tenant,
                    domain=dexit_config.domain_name,
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
                    domain=dexit_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_dexit_client.json",
                ),
                retry_policy=KeycloakClientSetupActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakClientSetupActivity.get_timeout(),
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
                "_manage-queues",
                "_manage-subscription",
                "_manage-faxes",
                "_manage-bulk-import",
                "_roi",
                "_reports",
                "_document-review",
            ]
            # keycloak client roles setup
            await workflow.execute_activity(
                activity=KeycloakCreateClientRolesActivity.defn,
                arg=KeycloakCreateClientRolesActivityModel(
                    client_name="dexit",
                    realm_name=realm_name,
                    roles=roles,
                ),
                retry_policy=KeycloakCreateClientRolesActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakCreateClientRolesActivity.get_timeout(),
            )

            # Create Service account
            client_secret = generate_password(length=32)

            await workflow.execute_activity(
                activity=OnePasswordCreateOrUpdateActivity.defn,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=tenant,
                    server_item=server_item,
                    vault=OnePasswordVaultName,
                    secret_name="service_account_secret",
                    secret_value=client_secret,
                ),
                retry_policy=OnePasswordCreateOrUpdateActivity.get_retry_policy(),
                start_to_close_timeout=OnePasswordCreateOrUpdateActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=KeycloakServiceAccountSetupActivity.defn,
                arg=KeycloakServiceAccountSetupActivityModel(
                    tenant=tenant,
                    domain=dexit_config.domain_name,
                    secret=client_secret,
                    realm_name=realm_name,
                    template_path=TemplatePath,
                    template_name="keycloak_service_account.json",
                ),
                retry_policy=KeycloakServiceAccountSetupActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakServiceAccountSetupActivity.get_timeout(),
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

            # Creating HF Inference Endpoints
            await workflow.execute_activity(
                activity=HFInferenceEndpointSetupActivity.defn,
                arg=dexit,
                retry_policy=HFInferenceEndpointSetupActivity.get_retry_policy(),
                start_to_close_timeout=HFInferenceEndpointSetupActivity.get_timeout(),
            )

            # setup tenant configmap
            for config_map in [
                {"name": "dexit-tenant-config", "key": "tenant-config.json"},
                {"name": "dexit-env-config", "key": "env-config.json"},
                {"name": "dexit-dicom-config", "key": "dicom-config.json"},
                {"name": "dexit-cli-vector-config", "key": "vector-config.toml"},
            ]:
                await workflow.execute_activity(
                    activity=K8sConfigMapCreationActivity.defn,
                    arg=K8sConfigMapCreationActivityModel(
                        namespace=tenant,
                        name=config_map["name"],
                        template_file_name=config_map["key"],
                        bucket_name="dexit-config",
                        template_payload={"tenant": tenant},
                    ),
                    retry_policy=K8sConfigMapCreationActivity.get_retry_policy(),
                    start_to_close_timeout=K8sConfigMapCreationActivity.get_timeout(),
                )

            # dns setup
            await workflow.execute_activity(
                activity=DnsSetupActivity.defn,
                arg=DnsSetupActivityModel(
                    cname=config.google_dns_cname,
                    fqdn=f"{tenant}.{dexit_config.domain_name}.",
                    zone_name=dexit_config.zone_name,
                ),
                retry_policy=DnsSetupActivity.get_retry_policy(),
                start_to_close_timeout=DnsSetupActivity.get_timeout(),
            )

            # ui setup
            repo_name = "dexit-ui"
            image_tag = "production" if config.env == "production" else "sprint"

            if config.env == "production":
                dest_dir = f"{tenant}.{dexit_config.domain_name}/"
            else:
                dest_dir = f"{tenant}.{dexit_config.domain_name}/{image_tag}"

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
                    job_name="dexit-atlas-migration-job",
                    docker_image=docker_image,
                    volume_mounts=[
                        {
                            "name": "dexit-env-config",
                            "mount_path": "/config/env-config.json",
                            "sub_path": "env-config.json",
                        },
                        {
                            "name": "dexit-tenant-config",
                            "mount_path": "/config/tenant-config.json",
                            "sub_path": "tenant-config.json",
                        },
                    ],
                    volumes=[
                        {
                            "name": "dexit-env-config",
                            "config_map_name": "dexit-env-config",
                            "key": "env-config.json",
                            "path": "env-config.json",
                        },
                        {
                            "name": "dexit-tenant-config",
                            "config_map_name": "dexit-tenant-config",
                            "key": "tenant-config.json",
                            "path": "tenant-config.json",
                        },
                    ],
                    container_envs=[
                        {"name": "APP_CONFIG_DIR", "value": "/config"},
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

            # kubernetes service
            await workflow.execute_activity(
                activity=KubernetesServiceActivity.defn,
                arg=KubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="dexit",
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
                    host=f"{tenant}.{dexit_config.domain_name}",
                    service_name="dexit-vs",
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
                    container_ports=[8000],
                    volume_mounts=[
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
                    ],
                    volumes=[
                        {
                            "name": "env-volume",
                            "config_map_name": "dexit-env-config",
                            "key": "env-config.json",
                            "path": "env-config.json",
                        },
                        {
                            "name": "tenant-volume",
                            "config_map_name": "dexit-tenant-config",
                            "key": "tenant-config.json",
                            "path": "tenant-config.json",
                        },
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "WEB_CONCURRENCY", "value": "5"},
                        {"name": "CLIENT_CODE", "value": tenant},
                        {"name": "APP_CONFIG_DIR", "value": "/config"},
                        {"name": "POSTGRES_PASSWORD", "value": postgres_password},
                        {"name": "POSTGRES_USER", "value": postgres_username},
                        {"name": "RELEASE_VERSION", "value": image_tag},
                        {"name": "TIKA_SERVER_ENDPOINT", "value": dexit_config.tika_server_endpoint},
                        {"name": "CLI", "value": "FALSE"},
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
                    name="dexit-worker",
                    docker_image=docker_image,
                    request_resource={
                        "cpu": pydash.get(dexit, "cliSpec.request_cpu"),
                        "memory": pydash.get(dexit, "cliSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(dexit, "cliSpec.limit_cpu"),
                        "memory": pydash.get(dexit, "cliSpec.limit_memory"),
                    },
                    container_ports=[8000],
                    volume_mounts=[
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
                        {"name": "vector-volume", "mount_path": "/vector", "read_only": True},
                    ],
                    volumes=[
                        {
                            "name": "env-volume",
                            "config_map_name": "dexit-env-config",
                            "key": "env-config.json",
                            "path": "env-config.json",
                        },
                        {
                            "name": "tenant-volume",
                            "config_map_name": "dexit-tenant-config",
                            "key": "tenant-config.json",
                            "path": "tenant-config.json",
                        },
                        {
                            "name": "vector-volume",
                            "config_map_name": "dexit-cli-vector-config",
                            "key": "vector-config.toml",
                            "path": "vector-config.toml",
                        },
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "CLIENT_CODE", "value": tenant},
                        {"name": "APP_CONFIG_DIR", "value": "/config"},
                        {"name": "POSTGRES_PASSWORD", "value": postgres_password},
                        {"name": "POSTGRES_USER", "value": postgres_username},
                        {"name": "RELEASE_VERSION", "value": image_tag},
                        {"name": "TIKA_SERVER_ENDPOINT", "value": dexit_config.tika_server_endpoint},
                        {"name": "CLI", "value": "TRUE"},
                    ],
                ),
                retry_policy=KubernetesStatefulSetActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesStatefulSetActivity.get_timeout(),
            )

            # statefulset pod creation for dicom
            await workflow.execute_activity(
                activity=KubernetesStatefulSetActivity.defn,
                arg=KubernetesStatefulSetActivityModel(
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
                    container_ports=[],
                    volume_mounts=[
                        {
                            "name": "dicom-volume",
                            "mount_path": "/etc/orthanc/orthanc.json",
                            "sub_path": "dicom-config.json",
                        },
                    ],
                    volumes=[
                        {
                            "name": "dicom-volume",
                            "config_map_name": "dexit-dicom-config",
                            "key": "dicom-config.json",
                            "path": "dicom-config.json",
                        },
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "WEB_CONCURRENCY", "value": "5"},
                        {"name": "CLIENT_CODE", "value": tenant},
                        {"name": "APP_CONFIG_DIR", "value": "/config"},
                        {"name": "RELEASE_VERSION", "value": image_tag},
                    ],
                ),
                retry_policy=KubernetesStatefulSetActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesStatefulSetActivity.get_timeout(),
            )

            # kubernetes service for dicom
            await workflow.execute_activity(
                activity=KubernetesServiceActivity.defn,
                arg=KubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="dexit-dicom",
                    port=8042,
                ),
                retry_policy=KubernetesServiceActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesServiceActivity.get_timeout(),
            )

            # vm pod scraper
            await workflow.execute_activity(
                activity=VMPodScrapperActivity.defn,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="dexit-metrics",
                    app="dexit",
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
                    namespace=f"dexit_{tenant}",
                ),
                retry_policy=TemporalNamespaceActivity.get_retry_policy(),
                start_to_close_timeout=TemporalNamespaceActivity.get_timeout(),
            )

            # temporal search attributes creation
            await workflow.execute_activity(
                activity=TemporalSearchAttributesCreationActivity.defn,
                arg=TemporalSearchAttributesCreationActivityModel(
                    namespace=f"dexit_{tenant}",
                ),
                retry_policy=TemporalSearchAttributesCreationActivity.get_retry_policy(),
                start_to_close_timeout=TemporalSearchAttributesCreationActivity.get_timeout(),
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
                    realm_name=realm_name,
                    tenant=tenant,
                    user_details={
                        "firstName": first_name,
                        "lastName": last_name,
                        "email": email,
                    },
                    domain_name=dexit_config.domain_name,
                    product=ProductName,
                    from_name=dexit_config.sender_name,
                    email_from=dexit_config.sender_email,
                ),
                retry_policy=SendAfterProvisioningMailActivity.get_retry_policy(),
                start_to_close_timeout=SendAfterProvisioningMailActivity.get_timeout(),
            )

        except Exception as e:
            workflow.logger.error(f"Error in onboarding workflow: {e}")
            await workflow.execute_activity(
                activity=UpdateTenantStatusActivity.defn,
                arg=TenantStatus(
                    tenant_name=pydash.get(dexit, "tenant"),
                    status="Failed",
                    error_msg=str(e),
                    product=ProductName,
                ),
                retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
                start_to_close_timeout=timedelta(seconds=120),
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
