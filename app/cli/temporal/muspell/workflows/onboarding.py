import asyncio
from collections.abc import Callable
from datetime import timedelta
from typing import TYPE_CHECKING

from app.cli.activity_util import run_activity
from app.cli.temporal.activities.cloudflare_setup import (
    AddBucketsToR2TokenActivity,
    CopyArtifactsToBucketActivity,
    CreateCloudflareBucketActivity,
    CreateCloudflareBucketCredentialsActivity,
    CreateCloudflareDNSRecordActivity,
    LinkBucketToDomainActivity,
    PropagateDNSRecordActivity,
    UpdateCORSForBucketActivity,
)
from app.cli.temporal.activities.deployment_pod_creation import (
    KedaApplyTemplatedYamlActivity,
    KedaApplyTemplatedYamlActivityModel,
    KubernetesDeploymentActivity,
    KubernetesDeploymentActivityModel,
    KubernetesDeploymentRestartActivity,
    KubernetesDeploymentRestartActivityModel,
)
from app.cli.temporal.activities.k8s_config_map import K8sConfigMapCreationActivity, K8sConfigMapCreationActivityModel
from app.cli.temporal.activities.k8s_istio_virtual_service import (
    KubernetesIstioVirtualServiceActivity,
    KubernetesIstioVirtualServiceActivityModel,
)
from app.cli.temporal.activities.k8s_namespace import K8sNamespaceCreationActivity, K8sNamespaceCreationActivityModel
from app.cli.temporal.activities.k8s_secret import K8sSecretCreationActivity, K8sSecretCreationActivityModel
from app.cli.temporal.activities.k8s_service import KubernetesServiceActivity, KubernetesServiceActivityModel
from app.cli.temporal.activities.keycloak_setup import (
    JeevesKeycloakCreateIDPFlowActivity,
    KeycloakClientSetupActivity,
    KeycloakClientSetupActivityModel,
    KeycloakCreateClientRolesActivity,
    KeycloakCreateClientRolesActivityModel,
    KeycloakCreateInternalUsersActivity,
    KeycloakCreateInternalUsersActivityModel,
    KeycloakCreateTenantCustomerAdminUserActivity,
    KeycloakCreateTenantCustomerAdminUserActivityModel,
    KeycloakGetClientSecretActivity,
    KeycloakGetClientSecretActivityModel,
    KeycloakGrantRealmManagementRolesActivity,
    KeycloakGrantRealmManagementRolesActivityModel,
    KeycloakRealmSetupActivity,
    KeycloakRealmSetupActivityModel,
    KeycloakServiceAccountSetupActivity,
    KeycloakServiceAccountSetupActivityModel,
    KeycloakSetUserAttributeActivity,
    KeycloakSetUserAttributeActivityModel,
)
from app.cli.temporal.activities.minio_setup import (
    AttachMinioPolicyActivity,
    CreateMinioBucketActivity,
    CreateMinioUserActivity,
)
from app.cli.temporal.activities.muspell_configupdate_job import (
    MuspellConfigUpdateJobActivity,
    MuspellConfigUpdateJobActivityModel,
)
from app.cli.temporal.activities.one_password import (
    CreatePasswordActivity,
    CreatePasswordActivityModel,
    OnePasswordCreateOrUpdateActivity,
    OnePasswordCreateOrUpdateActivityModel,
    OnePasswordInsertIfNotExistsActivity,
    OnePasswordInsertIfNotExistsActivityModel,
)
from app.cli.temporal.activities.postgres_setup import (
    KeycloakUserMappingActivity,
    KeycloakUserMappingActivityModel,
    PostgresCheckRoleExistsActivity,
    PostgresCheckRoleExistsActivityModel,
    PostgresDatabaseCreationActivity,
    PostgresDatabaseCreationActivityModel,
    PostgresGrantAccessToUserActivity,
    PostgresGrantAccessToUserActivityModel,
    PostgresGrantAllPrivilegesOnTableActivity,
    PostgresGrantAllPrivilegesOnTableActivityModel,
    PostgresGrantSupersetReadOnlyActivity,
    PostgresGrantSupersetReadOnlyActivityModel,
    PostgresSchemaCreationActivity,
    PostgresSchemaCreationActivityModel,
    PostgresUserCreationActivity,
    PostgresUserCreationActivityModel,
)
from app.cli.temporal.activities.redis import CACHE_HOST, RedisSetupActivity, RedisSetupActivityModel
from app.cli.temporal.activities.send_mail import (
    SendAfterProvisioningMailActivity,
    SendAfterProvisioningMailActivityModel,
)
from app.cli.temporal.activities.starrocks_setup import (
    CreateStarRocksCatalogActivity,
    CreateStarRocksUserActivity,
    StarRocksGrantReadOnlyCatalogActivity,
)
from app.cli.temporal.activities.stateful_set_pod_creation import (
    CheckPodRunningStatusActivity,
    CheckPodRunningStatusActivityModel,
)
from app.cli.temporal.activities.update_tenant_status import TenantCliStatus, UpdateTenantStatusActivity
from app.cli.temporal.activities.vm_pod_scrapper import VMPodScrapperActivity, VMPodScrapperActivityModel
from app.cli.temporal.core.base import Workflow
from app.cli.temporal.core.log import log_info
from app.cli.temporal.models.cloudflare import (
    AddBucketsToR2TokenActivityModel,
    CloudflareBucketCredentials,
    CopyArtifactsToBucketActivityModel,
    CreateCloudflareBucketActivityModel,
    CreateCloudflareBucketCredentialsActivityModel,
    CreateCloudflareDNSRecordActivityModel,
    LinkBucketToDomainActivityModel,
    PropagateDNSRecordActivityModel,
    UpdateCORSForBucketActivityModel,
)
from app.cli.temporal.models.starrocks import CreateStarRocksCatalogActivityModel
from app.cli.temporal.muspell import TemplatePath
from app.cli.temporal.muspell.models.muspellSpec import MuspellArchiveSpec
from app.common import generate_password
from app.core.ijson import ijson_dumps, ijson_loads
from app.starrocks_utils import GrantStarRocksReadOnlyCatalogModel, RegisterStarrocksUserModel

if TYPE_CHECKING:
    from app.core.product_settings.muspell_archive import MuspellArchiveSettings
import pydash
from temporalio import workflow

from app.core.settings import AppSettings, get_settings
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum
from app.template_env import get_env

ProductName = "muspell"
OnePasswordVaultName = "Muspell Archive"

# Grace period after the muspell-archive pod reports "Running" before seeding the
# `system` table, so its dbmate baseline (schema + config seed) has completed.
MUSPELL_DBMATE_SETTLE_SECONDS = 30

# Internal users provisioned into every muspell tenant realm. Single source of truth:
# the create-internal-users activity reads the full dicts; the post-seed Keycloak
# applicationaccess sync reads just the usernames. Add new entries here and both
# call sites pick them up automatically.
MUSPELL_INTERNAL_USERS: list[dict] = [
    {
        "username": "soumya.agarwal@314ecorp.com",
        "email": "soumya.agarwal@314ecorp.com",
        "firstname": "Soumya",
        "lastname": "Agrawal",
    },
]


@workflow.defn(name="MuspellOnboardingWorkflow", sandboxed=False)
class MuspellOnboardingWorkflow(Workflow):
    """
    Muspell Archive Onboarding Workflow
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
            K8sNamespaceCreationActivity.defn,
            K8sSecretCreationActivity.defn,
            KeycloakRealmSetupActivity.defn,
            KeycloakClientSetupActivity.defn,
            KeycloakCreateClientRolesActivity.defn,
            KeycloakServiceAccountSetupActivity.defn,
            KeycloakGetClientSecretActivity.defn,
            KeycloakGrantRealmManagementRolesActivity.defn,
            KeycloakCreateTenantCustomerAdminUserActivity.defn,
            CreateStarRocksCatalogActivity.defn,
            KubernetesDeploymentActivity.defn,
            KubernetesIstioVirtualServiceActivity.defn,
            KubernetesServiceActivity.defn,
            K8sConfigMapCreationActivity.defn,
            OnePasswordCreateOrUpdateActivity.defn,
            CheckPodRunningStatusActivity.defn,
            CreateCloudflareBucketActivity.defn,
            CreateCloudflareDNSRecordActivity.defn,
            LinkBucketToDomainActivity.defn,
            PropagateDNSRecordActivity.defn,
            CopyArtifactsToBucketActivity.defn,
            PostgresGrantAllPrivilegesOnTableActivity.defn,
            VMPodScrapperActivity.defn,
            CreateStarRocksUserActivity.defn,
            RedisSetupActivity.defn,
            UpdateCORSForBucketActivity.defn,
            CreateCloudflareBucketCredentialsActivity.defn,
            AddBucketsToR2TokenActivity.defn,
            OnePasswordInsertIfNotExistsActivity.defn,
            MuspellConfigUpdateJobActivity.defn,
            KubernetesDeploymentRestartActivity.defn,
            KeycloakCreateInternalUsersActivity.defn,
            KeycloakSetUserAttributeActivity.defn,
            JeevesKeycloakCreateIDPFlowActivity.defn,
            CreatePasswordActivity.defn,
            PostgresDatabaseCreationActivity.defn,
            CreateMinioUserActivity.defn,
            CreateMinioBucketActivity.defn,
            AttachMinioPolicyActivity.defn,
            KedaApplyTemplatedYamlActivity.defn,
            PostgresCheckRoleExistsActivity.defn,
            PostgresGrantSupersetReadOnlyActivity.defn,
            StarRocksGrantReadOnlyCatalogActivity.defn,
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", muspell: MuspellArchiveSpec) -> str:
        """
        Return workflow id
        """
        return f"muspell_onboarding_workflow_{pydash.get(muspell, 'tenant')}"

    @staticmethod
    def _build_app_systems(application_list_str: str | None) -> tuple[list[str], list[dict]]:
        """
        Parse the comma-separated `applicationList` spec input and mint one deterministic
        system UUID per application via `workflow.uuid4()` (replay-safe inside a workflow
        context — never use `uuid.uuid4`). The same UUIDs are threaded to BOTH the Keycloak
        `applicationaccess` attribute (keyed by system id) and the system-table seed activity,
        so the two agree on each system's UUID.
        """
        application_list = (
            [item.strip() for item in application_list_str.split(",") if item.strip()] if application_list_str else []
        )
        app_systems = [
            {
                "system_id": str(workflow.uuid4()),
                "name": name,
                "display_name": name,
                "database": name,
                "mnemonic": name[:3].upper(),
                "search_identifiers": [{"value": "mrn", "label": "MRN"}],
            }
            for name in application_list
        ]
        return application_list, app_systems

    @workflow.run
    async def run(self: "Workflow", muspell: MuspellArchiveSpec) -> None:
        """
        Run workflow
        """
        config: AppSettings = get_settings()
        muspell_config: MuspellArchiveSettings = config.muspell

        first_name = pydash.get(muspell, "firstName")
        last_name = pydash.get(muspell, "lastName")
        email = pydash.get(muspell, "email")
        tenant = pydash.get(muspell, "tenant")
        enable_mpi = pydash.get(muspell, "enableMpi")
        application_list, app_systems = self._build_app_systems(pydash.get(muspell, "applicationList"))
        log_info(f"Application list: {application_list}")

        try:
            await workflow.wait_condition(lambda: self.approved or self.deny)

            if self.deny:
                await run_activity(
                    activity=UpdateTenantStatusActivity,
                    arg=TenantCliStatus(
                        tenant_name=pydash.get(muspell, "tenant"),
                        status=TenantStatusEnum.Declined,
                        error_msg="Request Declined",
                        product=ProductEnum.muspell,
                    ),
                    start_to_close_timeout=timedelta(seconds=120),
                )
                return

            postgres_schema_name = tenant
            postgres_database_name = muspell_config.database_name
            postgres_username = f"{ProductName}_{tenant}"
            postgres_password = generate_password(length=20)
            database_url = (
                f"postgresql://{postgres_username}:{postgres_password}"
                f"@{config.postgres.host}:{config.postgres.port}"
                f"/{postgres_database_name}?sslmode=disable&application_name="
                f"{postgres_database_name}&options=-c search_path%3D{postgres_schema_name},public"
            )
            image_tag = "production" if config.env == "production" else "sprint"
            docker_image = f"registry.314ecorp.tech/muspell-app:{image_tag}"
            # Dedicated ROI export worker image (not the main app image). The KEDA
            # ScaledJob spins one of these per queued export request; the main app
            # server continues to run muspell-app.
            roi_docker_image = f"registry.314ecorp.tech/muspell-roi:{image_tag}"
            superset_docker_image = "registry.314ecorp.tech/superset:5.0.0"
            server_item = "production-config" if config.env == "production" else "integration-config"
            dicom_database_name = f"{ProductName}_dicom_{tenant}"
            dicom_database_password = await run_activity(
                activity=CreatePasswordActivity,
                arg=CreatePasswordActivityModel(length=20),
            )
            superset_schema_name = f"{tenant}_superset"

            # create postgres database for dicom
            await run_activity(
                activity=PostgresDatabaseCreationActivity,
                arg=PostgresDatabaseCreationActivityModel(
                    database_name=dicom_database_name,
                ),
            )

            # create postgres user for dicom
            await run_activity(
                activity=PostgresUserCreationActivity,
                arg=PostgresUserCreationActivityModel(
                    username=dicom_database_name,
                    database_name=dicom_database_name,
                    password=dicom_database_password,
                ),
            )

            # create one password for dicom database password
            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item=server_item,
                    vault=OnePasswordVaultName,
                    secret_name="pg_dicom_password",
                    secret_value=dicom_database_password,
                ),
            )

            await run_activity(
                activity=PostgresGrantAccessToUserActivity,
                arg=PostgresGrantAccessToUserActivityModel(
                    username=dicom_database_name,
                    database_name=dicom_database_name,
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item=server_item,
                    vault=OnePasswordVaultName,
                    secret_name="pg_username",
                    secret_value=postgres_username,
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item=server_item,
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

            # Optional read-only access for muspell_ro on the tenant schema (no-op if user absent)
            muspell_ro_exists = await run_activity(
                activity=PostgresCheckRoleExistsActivity,
                arg=PostgresCheckRoleExistsActivityModel(
                    username="muspell_ro",
                    database_name=postgres_database_name,
                ),
            )
            if muspell_ro_exists:
                await run_activity(
                    activity=PostgresGrantSupersetReadOnlyActivity,
                    arg=PostgresGrantSupersetReadOnlyActivityModel(
                        schema_name=postgres_schema_name,
                        schema_owner_username=postgres_username,
                        superset_ro_username="muspell_ro",
                        database_name=postgres_database_name,
                    ),
                )
            else:
                log_info(
                    f"Postgres role 'muspell_ro' not found; skipping read-only grant on schema {postgres_schema_name}"
                )

            await run_activity(
                activity=KeycloakUserMappingActivity,
                arg=KeycloakUserMappingActivityModel(
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
                        "user_role_mapping",
                        "federated_identity",
                        "user_group_membership",
                    ],
                ),
            )

            # create postgres schema and grant access for superset
            await run_activity(
                activity=PostgresSchemaCreationActivity,
                arg=PostgresSchemaCreationActivityModel(
                    schema_name=superset_schema_name,
                    username=postgres_username,
                    database_name=postgres_database_name,
                ),
            )

            await run_activity(
                activity=PostgresGrantAccessToUserActivity,
                arg=PostgresGrantAccessToUserActivityModel(
                    schema_name=superset_schema_name,
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
                    server_item=server_item,
                    vault=OnePasswordVaultName,
                    secret_name="redis_password",
                    secret_value=redis_tenant_password,
                ),
            )

            # dns setup for api
            await run_activity(
                activity=CreateCloudflareDNSRecordActivity,
                arg=CreateCloudflareDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{muspell_config.domain_name}",
                    zone_id=muspell_config.zone_id,
                    content=config.k8s_cname,
                ),
            )

            # create bucket
            bucket_name = f"{tenant}-{muspell_config.domain_name.replace('.', '-')}"
            await run_activity(
                activity=CreateCloudflareBucketActivity,
                arg=CreateCloudflareBucketActivityModel(bucket_name=bucket_name),
            )

            # link bucket to custom domain
            await run_activity(
                activity=LinkBucketToDomainActivity,
                arg=LinkBucketToDomainActivityModel(
                    bucket_name=bucket_name,
                    domain_name=f"{tenant}.{muspell_config.domain_name}",
                    zone_id=muspell_config.zone_id,
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
                                "headers": ["*"],
                            },
                            "exposeHeaders": ["ETag", "Content-Length", "Location", "Content-Disposition"],
                        }
                    ],
                ),
            )

            # ui setup
            repo_name = "muspell-ui"
            image_tag = "production" if config.env == "production" else "sprint"

            if config.env == "production":
                dest_dir = f"{bucket_name}/"
            else:
                dest_dir = f"{bucket_name}/{image_tag}"

            src_object_name = f"{repo_name}/{image_tag}/bundle.zip"

            bundle_path = "bundle/dist"

            if muspell_config.copy_ui_bundle:
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
                    retry_policy=CopyArtifactsToBucketActivity.get_retry_policy(),
                    start_to_close_timeout=CopyArtifactsToBucketActivity.get_timeout(),
                )

            credentials: CloudflareBucketCredentials = await run_activity(
                activity=CreateCloudflareBucketCredentialsActivity,
                arg=CreateCloudflareBucketCredentialsActivityModel(bucket_name=bucket_name, read_only=False),
            )

            # cdn base url added to onepassword
            base_url = f"https://{tenant}.{muspell_config.domain_name}"
            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item=server_item,
                    key="base_url_cdn",
                    key_value=base_url,
                ),
            )

            auth_url = config.keycloak.auth_url

            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item=server_item,
                    key="keycloak_auth_url",
                    key_value=auth_url,
                ),
            )

            # s3 bucket name added to onepassword
            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item=server_item,
                    key="s3_bucket_name",
                    key_value=bucket_name,
                ),
            )

            # s3 access key added to onepassword
            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item=server_item,
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
                    server_item=server_item,
                    key="s3_secret_key",
                    key_value=credentials.secret_key,
                ),
            )

            # only create these buckets for integration setup
            if config.env != "production":
                # create bucket in r2
                r2_bucket_name = f"ma-{tenant}"
                await run_activity(
                    activity=CreateCloudflareBucketActivity,
                    arg=CreateCloudflareBucketActivityModel(bucket_name=r2_bucket_name),
                )

                r2_credentials: CloudflareBucketCredentials = await run_activity(
                    activity=CreateCloudflareBucketCredentialsActivity,
                    arg=CreateCloudflareBucketCredentialsActivityModel(bucket_name=r2_bucket_name, read_only=False),
                )

                # r2 access key added to onepassword
                await run_activity(
                    activity=OnePasswordInsertIfNotExistsActivity,
                    arg=OnePasswordInsertIfNotExistsActivityModel(
                        tenant=f"{ProductName}_{tenant}",
                        vault=OnePasswordVaultName,
                        server_item=server_item,
                        key=f"{tenant}_r2_documents_bucket_name",
                        key_value=r2_bucket_name,
                    ),
                )

                # r2 access key added to onepassword
                await run_activity(
                    activity=OnePasswordInsertIfNotExistsActivity,
                    arg=OnePasswordInsertIfNotExistsActivityModel(
                        tenant=f"{ProductName}_{tenant}",
                        vault=OnePasswordVaultName,
                        server_item=server_item,
                        key=f"{tenant}_r2_documents_access_key",
                        key_value=r2_credentials.access_key,
                    ),
                )

                # r2 secret key added to onepassword
                await run_activity(
                    activity=OnePasswordInsertIfNotExistsActivity,
                    arg=OnePasswordInsertIfNotExistsActivityModel(
                        tenant=f"{ProductName}_{tenant}",
                        vault=OnePasswordVaultName,
                        server_item=server_item,
                        key=f"{tenant}_r2_documents_secret_key",
                        key_value=r2_credentials.secret_key,
                    ),
                )

                # r2 endpoint added to onepassword
                await run_activity(
                    activity=OnePasswordInsertIfNotExistsActivity,
                    arg=OnePasswordInsertIfNotExistsActivityModel(
                        tenant=f"{ProductName}_{tenant}",
                        vault=OnePasswordVaultName,
                        server_item=server_item,
                        key=f"{tenant}_r2_endpoint",
                        key_value=config.cloudflare.r2_endpoint,
                    ),
                )
                # bucket is shared across environments; allow both integration and prod UI origins
                await run_activity(
                    activity=UpdateCORSForBucketActivity,
                    arg=UpdateCORSForBucketActivityModel(
                        bucket_name=r2_bucket_name,
                        rules=[
                            {
                                "allowed": {
                                    "methods": ["GET", "PUT", "HEAD", "POST", "DELETE"],
                                    "origins": [base_url, f"https://{tenant}.muspell.com"],
                                    "headers": [
                                        "Authorization",
                                        "content-type",
                                        "x-amz-*",
                                        "traceparent",
                                        "If-Match",
                                        "If-None-Match",
                                    ],
                                },
                                "exposeHeaders": ["ETag", "Location"],
                            }
                        ],
                    ),
                )

                # Grant the shared read-only worker token access to this tenant's ma-<tenant>
                # bucket. Only in integration since ma-<tenant> only exists there. The activity
                # is idempotent and set-union-only — never removes buckets from the token's
                # existing scope.
                await run_activity(
                    activity=AddBucketsToR2TokenActivity,
                    arg=AddBucketsToR2TokenActivityModel(
                        token_name="muspell-zsc-worker-readonly-token",
                        bucket_names=[r2_bucket_name],
                        read_only=True,
                    ),
                )
                # endif integration specific flow

            # Extend the ma-{tenant} R2 token's scope to include this env's UI bucket (just created
            # above by CreateCloudflareBucketActivity). The token itself was created with only the
            # ma-{tenant} bucket in its policy by CreateCloudflareBucketCredentialsActivity inside
            # the non-prod block above; this call adds the UI bucket on top of that.
            #   Integration's call appends <tenant>-muspell-tech.
            #   Production's later call appends <tenant>-muspell-com on the same token.
            # The activity is idempotent and uses set-union, so prod's call preserves the
            # integration-appended entry while adding its own.
            await run_activity(
                activity=AddBucketsToR2TokenActivity,
                arg=AddBucketsToR2TokenActivityModel(
                    token_name=f"ma-{tenant}-app-token",
                    bucket_names=[bucket_name],
                ),
            )

            realm_name = tenant
            # keycloak realm setup
            await run_activity(
                activity=KeycloakRealmSetupActivity,
                arg=KeycloakRealmSetupActivityModel(
                    realm_name=realm_name,
                    domain=muspell_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_realm.json",
                    template_payload={"smtp_password": muspell_config.keycloak_smtp_password},
                ),
            )

            # keycloak client setup
            await run_activity(
                activity=KeycloakClientSetupActivity,
                arg=KeycloakClientSetupActivityModel(
                    tenant=tenant,
                    realm_name=realm_name,
                    domain=muspell_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_muspell_client.json",
                ),
            )

            roles = [
                "_can-access-patient-list",
                "_can-bypass-break-the-glass",
                "_can-control-access",
                "_can-create-edit-value-sets",
                "_can-launch-standalone",
                "_can-manage-streamline",
                "_can-merge-patient",
                "_can-purge-patient",
                "_can-release-information",
                "_can-save-document",
                "_can-share-feedback",
                "_can-upload-and-delete-documents",
                "_can-view-admin-settings",
                "_can-view-application-settings",
                "_can-view-reports",
                "_can-view-ssn",
                "_can-view-value-sets",
                "_developer",
                "_superset_Admin_CreateEditReports",
                "_superset_Admin_DeleteReports",
                "_superset_Admin_EngineerSQL",
                "_superset_Admin_ExportReports",
                "_superset_ViewReports",
            ]

            # keycloak client roles setup
            await run_activity(
                activity=KeycloakCreateClientRolesActivity,
                arg=KeycloakCreateClientRolesActivityModel(
                    client_name="muspell",
                    realm_name=realm_name,
                    roles=roles,
                ),
            )

            # `installer` service-account client. The muspell-archive server exchanges the
            # client_credentials for a token and calls Keycloak's admin API (create user,
            # update user attributes, etc.).
            #
            # Idempotency: Keycloak is the source of truth for the client secret. Ask
            # Keycloak first — if the `installer` client already exists we read its
            # current secret and mirror it into 1Password (CreateOrUpdate, so any
            # UI-side rotation propagates through). If the client doesn't exist yet we
            # mint a fresh 32-char secret and create the client with it. Either way,
            # 1Password and Keycloak end the step in lockstep.
            existing_installer_secret = await run_activity(
                activity=KeycloakGetClientSecretActivity,
                arg=KeycloakGetClientSecretActivityModel(
                    realm_name=realm_name,
                    client_name="installer",
                ),
            )
            installer_client_secret = existing_installer_secret or await run_activity(
                activity=CreatePasswordActivity,
                arg=CreatePasswordActivityModel(length=32),
            )
            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item=server_item,
                    secret_name="installer_client_secret",
                    secret_value=installer_client_secret,
                ),
            )
            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item=server_item,
                    secret_name="installer_client_id",
                    secret_value="installer",
                ),
            )
            await run_activity(
                activity=KeycloakServiceAccountSetupActivity,
                arg=KeycloakServiceAccountSetupActivityModel(
                    tenant=tenant,
                    domain=muspell_config.domain_name,
                    secret=installer_client_secret,
                    realm_name=realm_name,
                    template_path=TemplatePath,
                    template_name="keycloak_service_account.json",
                ),
            )
            # Grant the service-account user the realm-management roles the backend needs
            # to create/update users. Idempotent — Keycloak silently accepts duplicate
            # role assignments on re-runs.
            await run_activity(
                activity=KeycloakGrantRealmManagementRolesActivity,
                arg=KeycloakGrantRealmManagementRolesActivityModel(
                    realm_name=realm_name,
                    client_name="installer",
                    # view-clients: client_uuid + role resolution
                    # view-users: user reads, search, role-mapping reads (superset of query-users)
                    # manage-users: create/update/delete, password email, logout, role assign/remove
                    # view-identity-providers: /auth/idpHint + cdshook iss/aud validation
                    # view-realm: user-federation components
                    role_names=[
                        "view-clients",
                        "view-users",
                        "manage-users",
                        "view-identity-providers",
                        "view-realm",
                    ],
                ),
            )

            # keycloak idp setup
            await run_activity(
                activity=JeevesKeycloakCreateIDPFlowActivity,
                arg=KeycloakClientSetupActivityModel(
                    tenant=tenant,
                    realm_name=realm_name,
                    domain=muspell_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_idp_and_flows.json",
                    template_payload={"google_idp_secret": muspell_config.google_idp_secret},
                ),
            )

            template_env = get_env(template_path=TemplatePath)

            applicationaccess = None

            if application_list:
                applicationaccess_template = template_env.get_template("applicationaccess.json")
                # Keyed by system UUID (muspell-archive matches access by system id).
                applicationaccess_json = applicationaccess_template.render(app_systems=app_systems)
                applicationaccess = ijson_dumps(applicationaccess_json)

            # keycloak tenant customer admin user setup
            await run_activity(
                activity=KeycloakCreateTenantCustomerAdminUserActivity,
                arg=KeycloakCreateTenantCustomerAdminUserActivityModel(
                    realm_name=realm_name,
                    client_name="muspell",
                    username=email,
                    email=email,
                    firstname=first_name,
                    lastname=last_name,
                    template_path=TemplatePath,
                    template_name="keycloak_tenant_customer_admin.json",
                    template_payload={"applicationaccess": applicationaccess} if applicationaccess else None,
                    roles=[role for role in roles if role != "_developer"],
                ),
            )

            await run_activity(
                activity=KeycloakCreateInternalUsersActivity,
                arg=KeycloakCreateInternalUsersActivityModel(
                    realm_name=realm_name,
                    client_name="muspell",
                    template_path=TemplatePath,
                    template_name="keycloak_tenant_internal_user.json",
                    users=MUSPELL_INTERNAL_USERS,
                    template_payload={"applicationaccess": applicationaccess} if applicationaccess else None,
                    roles=[role for role in roles if role != "_developer"],
                ),
            )

            catalog_name = f"{tenant}"

            # Create the StarRocks catalog
            await run_activity(
                activity=CreateStarRocksCatalogActivity,
                arg=CreateStarRocksCatalogActivityModel(
                    tenant=tenant,
                    catalog_name=catalog_name,
                    warehouse_access_key=muspell_config.warehouse_access_key,
                    warehouse_secret_key=muspell_config.warehouse_secret_key,
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item=server_item,
                    secret_name="catalog",
                    secret_value=catalog_name,
                ),
            )

            starrocks_username = f"{ProductName}_{tenant}"
            starrocks_password = generate_password(length=20)

            # Create the StarRocks catalog
            await run_activity(
                activity=CreateStarRocksUserActivity,
                arg=RegisterStarrocksUserModel(
                    muspell_config=muspell_config,
                    tenant=tenant,
                    catalog_name=catalog_name,
                    user_name=starrocks_username,
                    user_password=starrocks_password,
                ),
            )

            # Optional read-only access for readonly_user on the tenant catalog (no-op if user absent)
            await run_activity(
                activity=StarRocksGrantReadOnlyCatalogActivity,
                arg=GrantStarRocksReadOnlyCatalogModel(
                    muspell_config=muspell_config,
                    user_name="readonly_user",
                    catalog_name=catalog_name,
                ),
            )

            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item=server_item,
                    key="sr_username",
                    key_value=starrocks_username,
                ),
            )

            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    vault=OnePasswordVaultName,
                    server_item=server_item,
                    key="sr_password",
                    key_value=starrocks_password,
                ),
            )

            tenant_config = "config.toml"
            code_system_config = "code_systems.toml"
            config_dir = "app/config"
            dicom_config = "dicom-config.json"

            # setup tenant configmap
            for config_map in [
                {
                    "name": "muspell-config",
                    "key": tenant_config,
                    "template_file_name": f"{config.env}-tenant-config.tmpl.toml",
                },
                {
                    "name": "muspell-config-system",
                    "key": code_system_config,
                    "template_file_name": f"{config.env}-tenant-system.tmpl.toml",
                },
                {
                    "name": "muspell-dicom-config",
                    "key": dicom_config,
                    "template_file_name": f"{config.env}-dicom-config.tmpl.json",
                },
            ]:
                await run_activity(
                    activity=K8sConfigMapCreationActivity,
                    arg=K8sConfigMapCreationActivityModel(
                        namespace=tenant,
                        name=config_map["name"],
                        template_file_name=config_map["template_file_name"],
                        destination_file_name=config_map["key"],
                        cloudflare_r2_folder_path="muspell-config",
                        template_payload={"tenant": tenant, "enableMPI": enable_mpi},
                    ),
                )

            # ROI export ScaledJob: Secret holding redis password → TriggerAuthentication → ScaledJob
            await run_activity(
                activity=K8sSecretCreationActivity,
                arg=K8sSecretCreationActivityModel(
                    namespace=tenant,
                    name="redis-credentials",
                    type="Opaque",
                    string_data={"REDIS_PASSWORD": redis_tenant_password},
                ),
            )

            await run_activity(
                activity=KedaApplyTemplatedYamlActivity,
                arg=KedaApplyTemplatedYamlActivityModel(
                    namespace=tenant,
                    template_path=TemplatePath,
                    template_name="keda-redis-trigger-auth.tmpl.yaml",
                    template_payload={"tenant": tenant},
                ),
            )

            await run_activity(
                activity=KedaApplyTemplatedYamlActivity,
                arg=KedaApplyTemplatedYamlActivityModel(
                    namespace=tenant,
                    template_path=TemplatePath,
                    template_name="keda-roi-export-scaledjob.tmpl.yaml",
                    template_payload={
                        "tenant": tenant,
                        "deployment": config.env,
                        "database_url": database_url,
                        "roi_docker_image": roi_docker_image,
                        "tenant_config": tenant_config,
                        "cache_host": CACHE_HOST,
                    },
                ),
            )

            # kubernetes service
            await run_activity(
                activity=KubernetesServiceActivity,
                arg=KubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="muspell-archive",
                    ports={"http": 8080},
                ),
            )

            template = template_env.get_template("istio-rules.json")
            output = template.render(
                tenant=tenant,
                image_tag=image_tag,
                env=config.env,
                domain_name=muspell_config.domain_name,
                kestra_basic_auth=muspell_config.kestra_basic_auth,
            )

            http_list = ijson_loads(output)

            # kubernetes virtual service
            await run_activity(
                activity=KubernetesIstioVirtualServiceActivity,
                arg=KubernetesIstioVirtualServiceActivityModel(
                    namespace=tenant,
                    host=f"{tenant}.api.{muspell_config.domain_name}",
                    service_name="muspell-vs",
                    payload=http_list,
                ),
            )

            # Deployment pod creation for server. dbmate migrations run in a dedicated init
            # container so the main container's image entrypoint no longer needs DATABASE_URL
            # in its environment (it reads postgres creds from config.toml at runtime).
            await run_activity(
                activity=KubernetesDeploymentActivity,
                arg=KubernetesDeploymentActivityModel(
                    namespace=tenant,
                    name="muspell-archive",
                    docker_image=docker_image,
                    request_resource={
                        "cpu": pydash.get(muspell, "serverSpec.request_cpu"),
                        "memory": pydash.get(muspell, "serverSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(muspell, "serverSpec.limit_cpu"),
                        "memory": pydash.get(muspell, "serverSpec.limit_memory"),
                    },
                    container_ports={"http": 8080},
                    volume_mounts=[
                        {
                            "name": "muspell-config",
                            "mount_path": f"/app/{tenant_config}",
                            "sub_path": tenant_config,
                        },
                        {
                            "name": "muspell-config-system",
                            "mount_path": f"/{config_dir}/{code_system_config}",
                            "sub_path": code_system_config,
                        },
                    ],
                    volumes=[
                        {
                            "name": "muspell-config",
                            "config_map_name": "muspell-config",
                            "key": tenant_config,
                            "path": tenant_config,
                        },
                        {
                            "name": "muspell-config-system",
                            "config_map_name": "muspell-config-system",
                            "key": code_system_config,
                            "path": code_system_config,
                        },
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                    ],
                    init_containers=[
                        {
                            "name": "migrate",
                            "image": docker_image,
                            "image_pull_policy": "Always",
                            "command": ["/usr/local/bin/dbmate", "--no-dump-schema", "migrate"],
                            "working_dir": "/app",
                            "env": [{"name": "DATABASE_URL", "value": database_url}],
                            "resources": {
                                "requests": {"cpu": "100m", "memory": "128Mi"},
                                "limits": {"cpu": "1", "memory": "512Mi"},
                            },
                        },
                    ],
                ),
            )

            # Deployment pod creation for dicom
            await run_activity(
                activity=KubernetesDeploymentActivity,
                arg=KubernetesDeploymentActivityModel(
                    namespace=tenant,
                    name="muspell-dicom",
                    docker_image="orthancteam/orthanc:24.8.1",
                    request_resource={
                        "cpu": pydash.get(muspell, "serverSpec.request_cpu"),
                        "memory": pydash.get(muspell, "serverSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(muspell, "serverSpec.limit_cpu"),
                        "memory": pydash.get(muspell, "serverSpec.limit_memory"),
                    },
                    container_ports={},
                    volume_mounts=[
                        {
                            "name": "dicom-volume",
                            "mount_path": "/etc/orthanc/orthanc.json",
                            "sub_path": dicom_config,
                        },
                    ],
                    volumes=[
                        {
                            "name": "dicom-volume",
                            "config_map_name": "muspell-dicom-config",
                            "key": dicom_config,
                            "path": dicom_config,
                        },
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "CLIENT_CODE", "value": tenant},
                        {"name": "APP_CONFIG_DIR", "value": f"/{config_dir}"},
                        {"name": "RELEASE_VERSION", "value": image_tag},
                    ],
                ),
            )

            # kubernetes service for dicom
            await run_activity(
                activity=KubernetesServiceActivity,
                arg=KubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="muspell-dicom",
                    ports={"http": 8042},
                ),
            )

            # vm pod scraper
            await run_activity(
                activity=VMPodScrapperActivity,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="muspell-metrics",
                    app="muspell-archive",
                    path="/metrics/",
                    interval="15s",
                ),
            )

            # propagate the dns record
            await run_activity(
                activity=PropagateDNSRecordActivity,
                arg=PropagateDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{muspell_config.domain_name}",
                ),
            )

            superset_password = generate_password(length=20)
            superset_secret_name = "superset-secrets"
            # Super setup for muspell
            await run_activity(
                activity=K8sSecretCreationActivity,
                arg=K8sSecretCreationActivityModel(
                    namespace=tenant,
                    name=superset_secret_name,
                    type="Opaque",
                    string_data={
                        "SUPERSET_SECRET_KEY": superset_password,
                        "DATABASE_PASSWORD": postgres_password,
                    },
                ),
            )

            await run_activity(
                activity=KubernetesDeploymentActivity,
                arg=KubernetesDeploymentActivityModel(
                    namespace=tenant,
                    name="muspell-superset",
                    docker_image=superset_docker_image,
                    request_resource={
                        "cpu": pydash.get(muspell, "serverSpec.request_cpu"),
                        "memory": pydash.get(muspell, "serverSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(muspell, "serverSpec.limit_cpu"),
                        "memory": pydash.get(muspell, "serverSpec.limit_memory"),
                    },
                    container_ports={"http": 8088},
                    volume_mounts=[],
                    volumes=[],
                    container_envs=[
                        {
                            "name": "SUPERSET_SECRET_KEY",
                            "value_from": {
                                "secret_key_ref": {"name": superset_secret_name, "key": "SUPERSET_SECRET_KEY"}
                            },
                        },
                        {
                            "name": "DATABASE_PASSWORD",
                            "value_from": {
                                "secret_key_ref": {"name": superset_secret_name, "key": "DATABASE_PASSWORD"}
                            },
                        },
                        {"name": "REDIS_PASSWORD", "value": redis_tenant_password},
                        {"name": "PYTHONUNBUFFERED", "value": "1"},
                        {"name": "COMPOSE_PROJECT_NAME", "value": "superset"},
                        {"name": "DEV_MODE", "value": "true"},
                        {"name": "DATABASE_SCHEMA", "value": superset_schema_name},
                        {"name": "DATABASE_DB", "value": postgres_database_name},
                        {"name": "DATABASE_HOST", "value": config.postgres.host},
                        {"name": "DATABASE_PORT", "value": str(config.postgres.port)},
                        {"name": "DATABASE_DIALECT", "value": "postgresql"},
                        {"name": "DATABASE_USER", "value": postgres_username},
                        {"name": "REDIS_HOST", "value": CACHE_HOST},
                        {"name": "REDIS_PORT", "value": "6379"},
                        {"name": "KEYCLOAK_CLIENT_ID", "value": "muspell"},
                        {"name": "KEYCLOAK_REALM", "value": tenant},
                        {"name": "KEYCLOAK_AUTH_URL", "value": f"{auth_url}/auth/"},
                        {"name": "SUPERSET_CONFIG_PATH", "value": "/app/superset_config.py"},
                        {
                            "name": "SUPERSET_BASE_URL",
                            "value": f"https://{tenant}.api.{muspell_config.domain_name}/superset",
                        },
                        {"name": "SCRIPT_NAME", "value": "/superset"},
                        {"name": "PYTHONPATH", "value": "/app/pythonpath:/app/docker/pythonpath_dev"},
                        {"name": "FLASK_DEBUG", "value": "true"},
                        {"name": "SUPERSET_ENV", "value": "production"},
                        {"name": "SUPERSET_LOAD_EXAMPLES", "value": "no"},
                        {"name": "CYPRESS_CONFIG", "value": "false"},
                        {"name": "SUPERSET_PORT", "value": "8088"},
                        {"name": "ENABLE_PLAYWRIGHT", "value": "false"},
                        {"name": "PUPPETEER_SKIP_CHROMIUM_DOWNLOAD", "value": "true"},
                        {"name": "BUILD_SUPERSET_FRONTEND_IN_DOCKER", "value": "false"},
                        {"name": "SUPERSET_LOG_LEVEL", "value": "info"},
                    ],
                ),
            )

            # kubernetes service for superset
            await run_activity(
                activity=KubernetesServiceActivity,
                arg=KubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="muspell-superset",
                    ports={"http": 8088},
                ),
            )

            # check pod running status
            for pod in ["muspell-archive", "muspell-dicom", "muspell-superset"]:
                await run_activity(
                    activity=CheckPodRunningStatusActivity,
                    arg=CheckPodRunningStatusActivityModel(
                        namespace=tenant,
                        name=pod,
                    ),
                    retry_policy=CheckPodRunningStatusActivity.get_retry_policy(),
                    start_to_close_timeout=CheckPodRunningStatusActivity.get_timeout(),
                )

            if app_systems:
                # The pod reports "Running" the moment the container starts —
                # before muspell-archive finishes its dbmate baseline (which
                # creates the `system` table + seeds config). Wait so those exist
                # before we seed the tenant's systems. The seed activity also
                # retries on failure as a backstop.
                await asyncio.sleep(MUSPELL_DBMATE_SETTLE_SECONDS)

                # Seed the `system` table (uuid-keyed, matching the Keycloak
                # applicationaccess). Everything else — organization globals incl.
                # enable_mpi, column, dataFlag, … — stays dbmate-baseline-default;
                # onboarding does not touch it. The activity returns the DB's
                # canonical {name: id} map — the existing id on conflict, the new
                # id on insert — used immediately below to re-align Keycloak.
                canonical_systems: dict[str, str] | None = await run_activity(
                    activity=MuspellConfigUpdateJobActivity,
                    arg=MuspellConfigUpdateJobActivityModel(
                        systems=app_systems,
                        schema_name=postgres_schema_name,
                        database_name=postgres_database_name,
                        username=postgres_username,
                        password=postgres_password,
                    ),
                )

                # Self-heal applicationaccess. The initial Keycloak user creation
                # (~line :807, :823) keyed applicationaccess by candidate ids
                # minted from workflow.uuid4(); insert_system.sql ON CONFLICT
                # keeps the DB's existing id, so on a re-run the two diverge. Push
                # the canonical map into Keycloak now — DB is the authority.
                # `None` guard: in-flight workflows recorded `None` from the
                # pre-fix activity; they skip this step gracefully and the next
                # re-run heals them.
                if canonical_systems:
                    canonical_app_systems = [
                        {**system, "system_id": canonical_systems.get(system["name"], system["system_id"])}
                        for system in app_systems
                    ]
                    # Pass the raw object string the template renders to. The
                    # python-keycloak SDK JSON-encodes the request payload once on
                    # the wire — wrapping in `ijson_dumps` here (as the initial-
                    # create path at :803-804 needs to for *template* substitution
                    # into keycloak_tenant_customer_admin.json) would double-encode
                    # and the stored attribute would require json.loads twice.
                    canonical_applicationaccess = template_env.get_template("applicationaccess.json").render(
                        app_systems=canonical_app_systems
                    )
                    await run_activity(
                        activity=KeycloakSetUserAttributeActivity,
                        arg=KeycloakSetUserAttributeActivityModel(
                            realm_name=realm_name,
                            usernames=[email, *(u["username"] for u in MUSPELL_INTERNAL_USERS)],
                            attribute_name="applicationaccess",
                            attribute_value=canonical_applicationaccess,
                        ),
                    )

                # Restart muspell-archive so its in-memory `systems` snapshot
                # reloads with the new rows (direct Postgres inserts don't fire
                # the app's CONFIG_CHANNEL refresh).
                await run_activity(
                    activity=KubernetesDeploymentRestartActivity,
                    arg=KubernetesDeploymentRestartActivityModel(
                        namespace=tenant,
                        name="muspell-archive",
                    ),
                )

                # Create pipeline for ETL job

            # update tenant status
            await run_activity(
                activity=UpdateTenantStatusActivity,
                arg=TenantCliStatus(
                    tenant_name=tenant, status=TenantStatusEnum.Provisioned, product=ProductEnum.muspell
                ),
            )

            # send mail
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
                    domain_name=muspell_config.domain_name,
                    product=ProductName,
                    from_name=muspell_config.sender_name,
                    email_from=muspell_config.sender_email,
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
                    product=ProductEnum.muspell,
                ),
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
