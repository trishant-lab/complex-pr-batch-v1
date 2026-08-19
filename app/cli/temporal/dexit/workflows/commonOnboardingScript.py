from collections.abc import Callable
from datetime import timedelta

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
    WorkersKVConfigUploadActivity,
    WorkersKVConfigUploadActivityModel,
)
from app.cli.temporal.activities.database_migration_job import (
    DatabaseMigrationJobActivity,
    DatabaseMigrationJobActivityModel,
)
from app.cli.temporal.activities.deployment_pod_creation import (
    KubernetesDeploymentActivity,
    KubernetesDeploymentActivityModel,
    KedaApplyTemplatedYamlActivity,
    KedaApplyTemplatedYamlActivityModel,
)
from app.cli.temporal.activities.dexit_zsegment_creation import ZSegmentSetupActivity
from app.cli.temporal.activities.dexit_novu_setup import DexitNovuSetupActivity
from app.cli.temporal.activities.fax_setup import FaxSetupActivity
from app.cli.temporal.activities.insert_subscription_details import (
    InsertSubscriptionDetailsActivity,
    InsertSubscriptionDetailsActivityModel,
)
from app.cli.temporal.activities.k8s_config_map import K8sConfigMapCreationActivity, K8sConfigMapCreationActivityModel
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
    DexitKeycloakCreateIDPFlowActivity,
    KeycloakAssignServiceAccountRoleActivity,
    KeycloakAssignServiceAccountRoleActivityModel,
    KeycloakClientSetupActivityModel,
    KeycloakCreateClientRolesActivity,
    KeycloakCreateClientRolesActivityModel,
    KeycloakCreateCompositeRolesActivity,
    KeycloakCreateCompositeRolesActivityModel,
    KeycloakCreateTenantCustomerAdminUserActivity,
    KeycloakCreateTenantCustomerAdminUserActivityModel,
    KeycloakRealmSetupActivity,
    KeycloakRealmSetupActivityModel,
    KeycloakServiceAccountSetupActivity,
    KeycloakServiceAccountSetupActivityModel,
    template_render,
)

from app.cli.temporal.activities.lago_service import LagoProperties, LagoSetupActivity
from app.cli.temporal.activities.one_password import (
    OnePasswordCreateOrUpdateActivity,
    OnePasswordCreateOrUpdateActivityModel,
    OnePasswordInsertIfNotExistsActivity,
    OnePasswordInsertIfNotExistsActivityModel,
    CreatePasswordActivity,
    CreatePasswordActivityModel,
)
from app.cli.temporal.activities.redis import (
    CACHE_HOST,
    CACHE_PORT,
    RedisSetupActivity,
    RedisSetupActivityModel,
)
from app.cli.temporal.activities.postgres_setup import (
    KeycloakUserMappingActivity,
    KeycloakUserMappingActivityModel,
    PostgresDatabaseCreationActivity,
    PostgresDatabaseCreationActivityModel,
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
    PostgresGrantSupersetReadOnlyActivity,
    PostgresGrantSupersetReadOnlyActivityModel,
)
from app.cli.temporal.activities.superset_setup import (
    SupersetTenantSetupActivity,
    SupersetTenantSetupActivityModel,
)
from app.cli.temporal.activities.send_mail import (
    SendAfterProvisioningMailActivity,
    SendAfterProvisioningMailActivityModel,
)
from app.cli.temporal.activities.stateful_set_pod_creation import (
    CheckPodRunningStatusActivity,
    CheckPodRunningStatusActivityModel,
)
from app.cli.temporal.activities.temporal_namespace import (
    TemporalNamespaceActivity,
    TemporalNamespaceActivityModel,
)
from app.cli.temporal.activities.temporal_search_atrributes_creation import (
    TemporalSearchAttributesCreationActivity,
    TemporalSearchAttributesCreationActivityModel,
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
from app.cli.temporal.dexit import TemplatePath
from app.cli.temporal.dexit.models.dexit_spec import DexitSpec
from app.cli.temporal.models.cloudflare import (
    CloudflareBucketCredentials,
    CopyArtifactsToBucketActivityModel,
    CreateCloudflareBucketActivityModel,
    CreateCloudflareBucketCredentialsActivityModel,
    CreateCloudflareDNSRecordActivityModel,
    LinkBucketToDomainActivityModel,
    PropagateDNSRecordActivityModel,
    UpdateCORSForBucketActivityModel,
)
from app.cli.temporal.zsegment.models.zsegment_spec import ZSegmentSpec
from app.core.ijson import ijson_loads
from app.core.settings import AppSettings, DexitSettings, get_settings
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum
from app.template_env import get_env

ProductName = "dexit"
OnePasswordVaultName = "Dexit"  # NOSONAR - This is a constant variable used for OnePassword vault name

# ConfigMap / Workers KV templates live under this prefix in the shared
# launchpad-config-templates bucket on R2, alongside the other products. The environment is a
# further level down so a production publish cannot overwrite what integration reads.
ConfigTemplateFolder = "dexit-config"


class DexitRole:
    """Keycloak client role names for the dexit product.

    Defined once here so the composite (system role) definitions reference the same
    identifiers as the atomic role list -- a typo fails at definition time instead of
    silently creating an orphan role or a composite that points at a non-existent child.
    """

    FAX_VIEW = "_fax-view"
    FAX_SEND = "_fax-send"
    FAX_BULK = "_fax-bulk"
    FILE_VIEW = "_file-view"
    DOCUMENT_VIEW = "_document-view"
    DOCUMENT_EDIT = "_document-edit"
    DOCUMENT_DELETE = "_document-delete"
    DOCUMENT_BULK_DELETE = "_document-bulk-delete"
    DOCUMENT_BULK_EXPORT = "_document-bulk-export"
    TASK_VIEW_ALL = "_task-view-all"
    TASK_ACTION = "_task-action"
    TASK_BULK = "_task-bulk"
    ANALYTICS_VIEW = "_analytics-view"
    AUDIT_VIEW = "_audit-view"
    SETTINGS_ACCOUNT = "_settings-account"
    SETTINGS_FAX_SETUP = "_settings-fax-setup"
    SETTINGS_WORKFLOW = "_settings-workflow"
    SETTINGS_USAGE = "_settings-usage"
    INTERNAL_ADMIN = "_internal-admin"


class DexitCommonOnboardingWorkflow(Workflow):
    """
    Dexit Onboarding Workflow
    """

    def __init__(self: "Workflow", is_onboarding: bool = False, approved: bool = False, denied: bool = False) -> None:
        self.is_onboarding: bool = is_onboarding
        self.approved: bool = approved
        self.denied: bool = denied

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
            PostgresGrantAllPrivilegesOnTableActivity.defn,
            K8sNamespaceCreationActivity.defn,
            K8sSecretCreationActivity.defn,
            DatabaseMigrationJobActivity.defn,
            DexitNovuSetupActivity.defn,
            KeycloakRealmSetupActivity.defn,
            KeycloakCreateClientRolesActivity.defn,
            KeycloakCreateCompositeRolesActivity.defn,
            KeycloakAssignServiceAccountRoleActivity.defn,
            KeycloakCreateTenantCustomerAdminUserActivity.defn,
            KubernetesDeploymentActivity.defn,
            KedaApplyTemplatedYamlActivity.defn,
            VMPodScrapperActivity.defn,
            KubernetesIstioVirtualServiceActivity.defn,
            KubernetesServiceActivity.defn,
            K8sConfigMapCreationActivity.defn,
            TemporalNamespaceActivity.defn,
            TemporalSearchAttributesCreationActivity.defn,
            FaxSetupActivity.defn,
            InsertSubscriptionDetailsActivity.defn,
            LagoSetupActivity.defn,
            OnePasswordCreateOrUpdateActivity.defn,
            PostgresDatabaseCreationActivity.defn,
            KeycloakServiceAccountSetupActivity.defn,
            CheckPodRunningStatusActivity.defn,
            CreateCloudflareBucketActivity.defn,
            WorkersKVConfigUploadActivity.defn,
            CreateCloudflareDNSRecordActivity.defn,
            LinkBucketToDomainActivity.defn,
            PropagateDNSRecordActivity.defn,
            CopyArtifactsToBucketActivity.defn,
            PostgresSupavisorPollUserActivity.defn,
            DexitKeycloakCreateIDPFlowActivity.defn,
            ZSegmentSetupActivity.defn,
            CreateCloudflareBucketCredentialsActivity.defn,
            UpdateCORSForBucketActivity.defn,
            OnePasswordInsertIfNotExistsActivity.defn,
            CreatePasswordActivity.defn,
            PostgresGrantSupersetReadOnlyActivity.defn,
            SupersetTenantSetupActivity.defn,
            RedisSetupActivity.defn,
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", dexit: DexitSpec) -> str:
        """
        Return workflow id

        """
        return f"dexit_onboarding_workflow_{pydash.get(dexit, 'tenant')}"

    async def starting_onboarding_activity(self: "Workflow", dexit: DexitSpec) -> bool:
        """
        Starting onboarding activity
        """
        if self.is_onboarding:
            await workflow.wait_condition(lambda: self.approved or self.denied)

            if self.denied:
                await run_activity(
                    activity=UpdateTenantStatusActivity,
                    arg=TenantCliStatus(
                        tenant_name=pydash.get(dexit, "tenant"),
                        status=TenantStatusEnum.ApprovalDeclined,
                        error_msg="Request Declined",
                        product=ProductEnum.dexit,
                    ),
                    start_to_close_timeout=timedelta(seconds=120),
                )
                return True
        return False

    async def _prepare_identity_provider_template_payload(
        self: "Workflow",
        tenant: str,
        domain_name: str,
        identity_providers: list[str] | None = None,
    ) -> dict:
        """
        Prepare identity provider template payload
        """
        if not identity_providers or len(identity_providers) == 0:
            return {"selectedIdentityProviders": [], "selectedIdentityProviderMappers": []}

        selected_idps = []
        selected_idps_mappers = []

        all_idps_configs = template_render(
            template_path=TemplatePath,
            template_name="dexit_idp_configs.tmpl.json",
            template_payload={
                "tenant": tenant,
                "domain": domain_name,
                "idp_config": get_settings().dexit.idp_config,
            },
        )
        all_idps_config_dict = ijson_loads(all_idps_configs)

        selected_idps = [idp for idp in all_idps_config_dict["identityProviders"] if idp["alias"] in identity_providers]

        selected_idps_mappers = [
            mapper
            for mapper in all_idps_config_dict["identityProviderMappers"]
            if mapper["identityProviderAlias"] in identity_providers
        ]

        return {
            "selectedIdentityProviders": selected_idps,
            "selectedIdentityProviderMappers": selected_idps_mappers,
        }

    async def _deploy_dicom_server(
        self: "Workflow",
        tenant: str,
        dexit: DexitSpec,
        config: AppSettings,
        server_item: str,
        config_dir: str,
    ) -> None:
        """
        Deploy DICOM server (Orthanc) for the tenant.
        Handles database creation, K8s deployment, service, and pod status check.
        """
        dicom_config = "dicom-config.json"
        dicom_database_name = f"{ProductName}_dicom_{tenant}"
        dicom_database_password = await run_activity(
            activity=CreatePasswordActivity,
            arg=CreatePasswordActivityModel(length=20),
        )

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
                tenant=tenant,
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

        # dicom configmap (per-env template under dexit-config on R2)
        await run_activity(
            activity=K8sConfigMapCreationActivity,
            arg=K8sConfigMapCreationActivityModel(
                namespace=tenant,
                name="dexit-dicom-config",
                template_file_name="dexit-dicom-config.tmpl.json",
                destination_file_name=dicom_config,
                cloudflare_r2_folder_path=f"{ConfigTemplateFolder}/{config.env}",
                template_payload={"tenant": tenant, "env": config.env},
                drop_empty_secrets=True,
            ),
        )

        # statefulset pod creation for dicom
        await run_activity(
            activity=KubernetesDeploymentActivity,
            arg=KubernetesDeploymentActivityModel(
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
                        "config_map_name": "dexit-dicom-config",
                        "key": dicom_config,
                        "path": dicom_config,
                    },
                ],
                container_envs=[
                    {"name": "DEPLOYMENT", "value": config.env},
                    {"name": "WEB_CONCURRENCY", "value": "5"},
                    {"name": "APP_CONFIG_DIR", "value": f"/{config_dir}"},
                ],
            ),
        )

        # kubernetes service for dicom
        await run_activity(
            activity=KubernetesServiceActivity,
            arg=KubernetesServiceActivityModel(
                namespace=tenant,
                service_name="dexit-dicom",
                ports={"http": 8042},
            ),
        )

        # check dicom pod running status
        await run_activity(
            activity=CheckPodRunningStatusActivity,
            arg=CheckPodRunningStatusActivityModel(
                namespace=tenant,
                name="dexit-dicom",
            ),
            retry_policy=CheckPodRunningStatusActivity.get_retry_policy(),
            start_to_close_timeout=CheckPodRunningStatusActivity.get_timeout(),
        )

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
        identity_providers = pydash.get(dexit, "identityProviders")
        zsegment_provisioning = pydash.get(dexit, "zsegmentProvisioning", "").lower() == "true"
        deploy_dicom_server = pydash.get(dexit, "deployDicomServer").lower() == "true"
        dexit_superset_ro_username = "dexit_superset_ro"
        try:
            if await self.starting_onboarding_activity(dexit):
                return

            postgres_schema_name = tenant
            postgres_database_name = "dexit"
            postgres_username = f"{ProductName}_{tenant}"

            postgres_password = await run_activity(
                activity=CreatePasswordActivity,
                arg=CreatePasswordActivityModel(length=20),
            )

            image_tag = "production" if config.env == "production" else "sprint"
            docker_image = f"registry.314ecorp.tech/dexit-app:{image_tag}"
            server_item = f"{config.env}-config"

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
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=tenant,
                    server_item=server_item,
                    vault=OnePasswordVaultName,
                    secret_name="pg_password",
                    secret_value=postgres_password,
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

            # Superset tenant user provisioning
            superset_tenant_password = await run_activity(
                activity=CreatePasswordActivity,
                arg=CreatePasswordActivityModel(length=20),
            )

            await run_activity(
                activity=SupersetTenantSetupActivity,
                arg=SupersetTenantSetupActivityModel(
                    tenant=tenant,
                    first_name=ProductName.capitalize(),
                    last_name=tenant,
                    email=email,
                    superset_base_url=dexit_config.superset.base_url,
                    superset_admin_username=dexit_config.superset.admin_username,
                    superset_admin_password=dexit_config.superset.admin_password,
                    tenant_password=superset_tenant_password,
                    product_group="Dexit",
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=tenant,
                    server_item=server_item,
                    vault=OnePasswordVaultName,
                    secret_name="superset_base_url",
                    secret_value=f"https://{tenant}.{dexit_config.domain_name}/insights",
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=tenant,
                    server_item=server_item,
                    vault=OnePasswordVaultName,
                    secret_name="superset_username",
                    secret_value=tenant,
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=tenant,
                    server_item=server_item,
                    vault=OnePasswordVaultName,
                    secret_name="superset_password",
                    secret_value=superset_tenant_password,
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
                activity=PostgresGrantAllPrivilegesOnTableActivity,
                arg=PostgresGrantAllPrivilegesOnTableActivityModel(
                    database_name=postgres_database_name,
                    username=postgres_username,
                    tables=[
                        "user_entity",
                        "user_required_action",
                        "realm",
                        "user_attribute",
                        "keycloak_role",
                        "user_role_mapping",
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

            # setup subscription
            lago_plan_code = pydash.get(dexit, "planName", "Basic")
            subscription_result = await run_activity(
                activity=InsertSubscriptionDetailsActivity,
                arg=InsertSubscriptionDetailsActivityModel(
                    tenant_name=tenant,
                    product=ProductEnum.dexit,
                    plancode=lago_plan_code,
                    name="Active Subscription",
                ),
            )

            # setup lago
            external_customer_id = subscription_result.customer_id
            lago_subscription_id = subscription_result.subscription_id
            lago_api_key = dexit_config.lago.api_key
            lago_api_url = dexit_config.lago.api_url

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=tenant,
                    server_item=server_item,
                    vault=OnePasswordVaultName,
                    secret_name="external_customer_id",
                    secret_value=str(external_customer_id),
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=tenant,
                    server_item=server_item,
                    vault=OnePasswordVaultName,
                    secret_name="lago_subscription_id",
                    secret_value=str(lago_subscription_id),
                ),
            )

            await run_activity(
                activity=LagoSetupActivity,
                arg=LagoProperties(
                    tenant=tenant,
                    customer_id=external_customer_id,
                    customer_name=tenant,
                    customer_email=email,
                    subscription_id=lago_subscription_id,
                    plan_code=lago_plan_code,
                    api_key=lago_api_key,
                    api_url=lago_api_url,
                ),
            )

            # setup novu
            await run_activity(activity=DexitNovuSetupActivity, arg=dexit)

            fax_webhook_secret = await run_activity(
                activity=CreatePasswordActivity,
                arg=CreatePasswordActivityModel(length=32),
            )

            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=tenant,
                    vault=OnePasswordVaultName,
                    server_item=server_item,
                    key="webhook_secret",
                    key_value=fax_webhook_secret,
                ),
            )

            # fax setup
            await run_activity(activity=FaxSetupActivity, arg=dexit)

            realm_name = tenant
            template_payload = await self._prepare_identity_provider_template_payload(
                tenant=tenant,
                identity_providers=identity_providers,
                domain_name=dexit_config.domain_name,
            )

            # keycloak realm setup
            await run_activity(
                activity=KeycloakRealmSetupActivity,
                arg=KeycloakRealmSetupActivityModel(
                    realm_name=realm_name,
                    domain=dexit_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_realm.json",
                    template_payload=template_payload,
                ),
            )

            roles = [
                DexitRole.FAX_VIEW,
                DexitRole.FAX_SEND,
                DexitRole.FAX_BULK,
                DexitRole.FILE_VIEW,
                DexitRole.DOCUMENT_VIEW,
                DexitRole.DOCUMENT_EDIT,
                DexitRole.DOCUMENT_DELETE,
                DexitRole.DOCUMENT_BULK_DELETE,
                DexitRole.DOCUMENT_BULK_EXPORT,
                DexitRole.TASK_VIEW_ALL,
                DexitRole.TASK_ACTION,
                DexitRole.TASK_BULK,
                DexitRole.ANALYTICS_VIEW,
                DexitRole.AUDIT_VIEW,
                DexitRole.SETTINGS_ACCOUNT,
                DexitRole.SETTINGS_FAX_SETUP,
                DexitRole.SETTINGS_WORKFLOW,
                DexitRole.SETTINGS_USAGE,
            ]

            composites = {
                "Admin": roles,
                "Member": [
                    DexitRole.FAX_VIEW,
                    DexitRole.FAX_SEND,
                    DexitRole.FILE_VIEW,
                    DexitRole.DOCUMENT_VIEW,
                    DexitRole.DOCUMENT_EDIT,
                    DexitRole.TASK_VIEW_ALL,
                    DexitRole.TASK_ACTION,
                    DexitRole.ANALYTICS_VIEW,
                ],
                "Viewer": [
                    DexitRole.FAX_VIEW,
                    DexitRole.FILE_VIEW,
                    DexitRole.DOCUMENT_VIEW,
                    DexitRole.TASK_VIEW_ALL,
                    DexitRole.ANALYTICS_VIEW,
                ],
            }

            # keycloak client roles setup
            await run_activity(
                activity=KeycloakCreateClientRolesActivity,
                arg=KeycloakCreateClientRolesActivityModel(
                    client_name=ProductName,
                    realm_name=realm_name,
                    roles=[*roles, DexitRole.INTERNAL_ADMIN],
                ),
            )

            # keycloak composite (system) roles setup
            await run_activity(
                activity=KeycloakCreateCompositeRolesActivity,
                arg=KeycloakCreateCompositeRolesActivityModel(
                    client_name=ProductName,
                    realm_name=realm_name,
                    composites=composites,
                ),
            )

            # Create Service account
            client_secret = await run_activity(
                activity=CreatePasswordActivity,
                arg=CreatePasswordActivityModel(length=32),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=tenant,
                    server_item=server_item,
                    vault=OnePasswordVaultName,
                    secret_name="service_account_secret",
                    secret_value=client_secret,
                ),
            )

            await run_activity(
                activity=KeycloakServiceAccountSetupActivity,
                arg=KeycloakServiceAccountSetupActivityModel(
                    tenant=tenant,
                    domain=dexit_config.domain_name,
                    secret=client_secret,
                    realm_name=realm_name,
                    template_path=TemplatePath,
                    template_name="keycloak_service_account.json",
                ),
            )

            # grant the shared service account the dexit Admin composite (broad access;
            # used cross-product, e.g. zsegment authenticates through it)
            await run_activity(
                activity=KeycloakAssignServiceAccountRoleActivity,
                arg=KeycloakAssignServiceAccountRoleActivityModel(
                    sa_client_name="service-account",
                    target_client_name=ProductName,
                    role_name="Admin",
                    realm_name=realm_name,
                ),
            )

            # Create IDP mappers
            await workflow.execute_activity(
                activity=DexitKeycloakCreateIDPFlowActivity.defn,
                arg=KeycloakClientSetupActivityModel(
                    tenant=tenant,
                    realm_name="dexithelp",
                    domain=dexit_config.domain_name,
                    template_path=TemplatePath,
                    template_name="dexithelp_instance_idp_flow.json",
                    template_payload={"idp_config": dexit_config.idp_config, "auth_url": config.keycloak.auth_url},
                    is_prod=True,
                ),
                retry_policy=DexitKeycloakCreateIDPFlowActivity.get_retry_policy(),
                start_to_close_timeout=DexitKeycloakCreateIDPFlowActivity.get_timeout(),
            )

            # keycloak tenant customer admin user setup
            await workflow.execute_activity(
                activity=KeycloakCreateTenantCustomerAdminUserActivity.defn,
                arg=KeycloakCreateTenantCustomerAdminUserActivityModel(
                    realm_name=realm_name,
                    client_name=ProductName,
                    username=email,
                    email=email,
                    firstname=first_name,
                    lastname=last_name,
                    template_path=TemplatePath,
                    roles=roles,
                    template_name="keycloak_user.json",
                ),
                retry_policy=KeycloakCreateTenantCustomerAdminUserActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakCreateTenantCustomerAdminUserActivity.get_timeout(),
            )

            # dns setup for api
            await run_activity(
                activity=CreateCloudflareDNSRecordActivity,
                arg=CreateCloudflareDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{dexit_config.domain_name}",
                    zone_id=dexit_config.zone_id,
                    content=config.k8s_cname,
                ),
            )

            # create bucket
            bucket_name = f"{tenant}-{dexit_config.domain_name.replace('.', '-')}"
            await run_activity(
                activity=CreateCloudflareBucketActivity,
                arg=CreateCloudflareBucketActivityModel(bucket_name=bucket_name),
            )

            # link bucket to custom domain
            await run_activity(
                activity=LinkBucketToDomainActivity,
                arg=LinkBucketToDomainActivityModel(
                    bucket_name=bucket_name,
                    domain_name=f"{tenant}.{dexit_config.domain_name}",
                    zone_id=dexit_config.zone_id,
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
                            "exposeHeaders": ["ETag", "Location", "Content-Disposition"],
                        }
                    ],
                ),
            )

            # propagate the dns record
            await run_activity(
                activity=PropagateDNSRecordActivity,
                arg=PropagateDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{dexit_config.domain_name}",
                ),
            )

            # ui setup
            repo_name = "dexit-ui"
            src_object_name = f"{repo_name}/{image_tag}/bundle.zip"
            bundle_path = "bundle/dist/admin"
            dest_dir = f"{bucket_name}/" if config.env == "production" else f"{bucket_name}/{image_tag}"
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

            # s3 bucket name added to onepassword
            await run_activity(
                activity=OnePasswordInsertIfNotExistsActivity,
                arg=OnePasswordInsertIfNotExistsActivityModel(
                    tenant=tenant,
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
                    tenant=tenant,
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
                    tenant=tenant,
                    vault=OnePasswordVaultName,
                    server_item=server_item,
                    key="s3_secret_key",
                    key_value=credentials.secret_key,
                ),
            )

            app_config_file = "app-config.json"
            config_dir = "config"

            redis_tenant_password = await run_activity(
                activity=CreatePasswordActivity,
                arg=CreatePasswordActivityModel(length=20),
            )

            await run_activity(
                activity=K8sSecretCreationActivity,
                arg=K8sSecretCreationActivityModel(
                    namespace=tenant,
                    name="dexit-redis",
                    string_data={"password": redis_tenant_password},
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

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=tenant,
                    server_item=server_item,
                    vault=OnePasswordVaultName,
                    secret_name="redis_dns",
                    secret_value=f"redis://:{redis_tenant_password}@{CACHE_HOST}:{CACHE_PORT}",
                ),
            )

            # Worker user (referenced by configmap and by Workers KV template below)
            worker_user_password = await run_activity(
                activity=CreatePasswordActivity,
                arg=CreatePasswordActivityModel(length=20),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=tenant,
                    server_item=server_item,
                    vault=OnePasswordVaultName,
                    secret_name="worker_username",
                    secret_value=f"{tenant}fax",
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=tenant,
                    server_item=server_item,
                    vault=OnePasswordVaultName,
                    secret_name="worker_password",
                    secret_value=worker_user_password,
                ),
            )

            # Cloudflare per-tenant pointers (sourced from settings, not generated)

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=tenant,
                    server_item=server_item,
                    vault=OnePasswordVaultName,
                    secret_name="cf_api_token",
                    secret_value=config.cloudflare.api_token,
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=tenant,
                    server_item=server_item,
                    vault=OnePasswordVaultName,
                    secret_name="cf_account_id",
                    secret_value=config.cloudflare.account_id,
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=tenant,
                    server_item=server_item,
                    vault=OnePasswordVaultName,
                    secret_name="cf_kv_namespace_id",
                    secret_value=dexit_config.cloudflare_worker_settings.workers_kv_namespace_id,
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=tenant,
                    server_item=server_item,
                    vault=OnePasswordVaultName,
                    secret_name="cf_queue_id",
                    secret_value=dexit_config.cloudflare_worker_settings.cf_queue_id,
                ),
            )

            # setup tenant configmap — single app-config covers server, CLI workers, dbmate job
            await run_activity(
                activity=K8sConfigMapCreationActivity,
                arg=K8sConfigMapCreationActivityModel(
                    namespace=tenant,
                    name="dexit-app-config",
                    template_file_name="dexit-app-config.tmpl.json",
                    destination_file_name=app_config_file,
                    cloudflare_r2_folder_path=f"{ConfigTemplateFolder}/{config.env}",
                    template_payload={
                        "tenant": tenant,
                        "env": config.env,
                        "domain": dexit_config.domain_name,
                    },
                    drop_empty_secrets=True,
                ),
            )

            # dbmate job — migrations first, then seed the initial model rows into the tenant schema
            # (dexit-app resolves the schema from db_schema_name in the mounted app-config)
            await run_activity(
                activity=DatabaseMigrationJobActivity,
                arg=DatabaseMigrationJobActivityModel(
                    namespace=tenant,
                    job_name="dexit-dbmate-migration-job",
                    docker_image=docker_image,
                    volume_mounts=[
                        {
                            "name": "dexit-app-config",
                            "mount_path": f"/{config_dir}/{app_config_file}",
                            "sub_path": app_config_file,
                        },
                    ],
                    volumes=[
                        {
                            "name": "dexit-app-config",
                            "config_map_name": "dexit-app-config",
                            "key": app_config_file,
                            "path": app_config_file,
                        },
                    ],
                    container_envs=[
                        {"name": "APP_CONFIG_DIR", "value": f"/{config_dir}"},
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "POSTGRES_PASSWORD", "value": postgres_password},
                        {"name": "POSTGRES_USER", "value": f"{postgres_username}.{postgres_username}"},
                    ],
                    argument=(
                        "python3 /app/provisioning/dbmate_migration.py"
                        " && python3 -m app.mlopshelper.deployinitialmodels"
                    ),
                    job_type="dbmate",
                    product=ProductName,
                ),
            )

            await run_activity(
                activity=PostgresGrantSupersetReadOnlyActivity,
                arg=PostgresGrantSupersetReadOnlyActivityModel(
                    schema_name=postgres_schema_name,
                    schema_owner_username=postgres_username,
                    database_name=postgres_database_name,
                    superset_ro_username=dexit_superset_ro_username,
                ),
            )

            # kubernetes service
            await run_activity(
                activity=KubernetesServiceActivity,
                arg=KubernetesServiceActivityModel(
                    namespace=tenant,
                    ports={"http": 8000},
                    service_name="dexit",
                ),
            )

            template_env = get_env(template_path=TemplatePath)
            template = template_env.get_template("istio-rules.json")
            output = template.render(tenant=tenant, image_tag=image_tag, env=config.env)

            http_list = ijson_loads(output)

            if not deploy_dicom_server:
                http_list = [rule for rule in http_list if rule.get("name") != "dexit-dicom"]

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
                    host=f"{tenant}.api.{dexit_config.domain_name}",
                    service_name="dexit-vs",
                    payload=http_list,
                ),
            )

            await run_activity(
                activity=WorkersKVConfigUploadActivity,
                arg=WorkersKVConfigUploadActivityModel(
                    namespace_id=dexit_config.cloudflare_worker_settings.workers_kv_namespace_id,
                    key=tenant,
                    template_file_name="dexit-worker-kv-config.tmpl.json",
                    template_payload={
                        "tenant": tenant,
                        "env": config.env,
                        "domain": dexit_config.domain_name,
                    },
                    cloudflare_r2_folder_path=f"{ConfigTemplateFolder}/{config.env}",
                ),
            )

            # statefulset pod creation for server
            await run_activity(
                activity=KubernetesDeploymentActivity,
                arg=KubernetesDeploymentActivityModel(
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
                    container_ports={"http": 8000},
                    volume_mounts=[
                        {
                            "name": "dexit-app-config",
                            "mount_path": f"/{config_dir}/{app_config_file}",
                            "sub_path": app_config_file,
                        },
                    ],
                    volumes=[
                        {
                            "name": "dexit-app-config",
                            "config_map_name": "dexit-app-config",
                            "key": app_config_file,
                            "path": app_config_file,
                        },
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "WEB_CONCURRENCY", "value": "5"},
                        {"name": "APP_CONFIG_DIR", "value": f"/{config_dir}"},
                        {"name": "POSTGRES_PASSWORD", "value": postgres_password},
                        {"name": "POSTGRES_USER", "value": f"{postgres_username}.{postgres_username}"},
                        {"name": "CLI", "value": "FALSE"},
                    ],
                ),
            )

            # temporal namespace creation (must be before worker pods so they can connect on startup)
            await run_activity(
                activity=TemporalNamespaceActivity,
                arg=TemporalNamespaceActivityModel(
                    namespace=f"dexit_{tenant}",
                ),
            )

            # temporal search attributes creation
            await run_activity(
                activity=TemporalSearchAttributesCreationActivity,
                arg=TemporalSearchAttributesCreationActivityModel(
                    namespace=f"dexit_{tenant}",
                ),
            )

            # statefulset pod creation for cli
            cli_pods = {
                "dexit-worker-all": "all_workers",
                "dexit-worker-dsl": "dsl_processing_worker",
                "dexit-worker-dslp": "dsl_processing_worker_priority",
                "dexit-worker-event": "event_processing_worker",
                "dexit-worker-ml": "ml_workers",
                "dexit-training-worker": "training_worker",
            }

            for key, value in cli_pods.items():
                await run_activity(
                    activity=KubernetesDeploymentActivity,
                    arg=KubernetesDeploymentActivityModel(
                        namespace=tenant,
                        name=key,
                        docker_image=docker_image,
                        request_resource={
                            "cpu": pydash.get(dexit, "cliSpec.request_cpu"),
                            "memory": pydash.get(dexit, "cliSpec.request_memory"),
                        },
                        limit_resource={
                            "cpu": pydash.get(dexit, "cliSpec.limit_cpu"),
                            "memory": pydash.get(dexit, "cliSpec.limit_memory"),
                        },
                        container_ports={"http": 8000},
                        volume_mounts=[
                            {
                                "name": "dexit-app-config",
                                "mount_path": f"/{config_dir}/{app_config_file}",
                                "sub_path": app_config_file,
                            },
                        ],
                        volumes=[
                            {
                                "name": "dexit-app-config",
                                "config_map_name": "dexit-app-config",
                                "key": app_config_file,
                                "path": app_config_file,
                            },
                        ],
                        container_envs=[
                            {"name": "DEPLOYMENT", "value": config.env},
                            {"name": "APP_CONFIG_DIR", "value": f"/{config_dir}"},
                            {"name": "POSTGRES_PASSWORD", "value": postgres_password},
                            {"name": "POSTGRES_USER", "value": f"{postgres_username}.{postgres_username}"},
                            {"name": "CLI", "value": "TRUE"},
                            {"name": "WORKER_TYPE", "value": value},
                        ],
                    ),
                )

            # vm pod scraper
            await run_activity(
                activity=VMPodScrapperActivity,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="dexit-metrics",
                    app="dexit",
                    path="/metrics/",
                    interval="15s",
                ),
            )

            # check pod running status
            for pod in ["dexit", *list(cli_pods.keys())]:
                await run_activity(
                    activity=CheckPodRunningStatusActivity,
                    arg=CheckPodRunningStatusActivityModel(
                        namespace=tenant,
                        name=pod,
                    ),
                    retry_policy=CheckPodRunningStatusActivity.get_retry_policy(),
                    start_to_close_timeout=CheckPodRunningStatusActivity.get_timeout(),
                )

            # zsegment onboarding
            if zsegment_provisioning:
                await run_activity(
                    activity=ZSegmentSetupActivity,
                    arg=ZSegmentSpec(tenant=tenant, email=email, firstName=first_name, lastName=last_name),
                )
                workflow.logger.info(f"Created new Zsegment tenant: {tenant}")

            # Apply worker scaling templates
            scaling_templates = [
                "temporal-worker-all-scaling.yaml",
                "temporal-worker-dsl-scaling.yaml",
                "temporal-worker-dslp-scaling.yaml",
                "temporal-worker-event-scaling.yaml",
            ]
            for template_name in scaling_templates:
                yaml_content = template_render(
                    template_path=TemplatePath,
                    template_name=template_name,
                    template_payload={
                        "tenant": tenant,
                        "max_replica_count": dexit_config.worker_max_replica_count,
                        "min_replica_count": dexit_config.worker_min_replica_count,
                        "vm_metrics_server_address": dexit_config.get_vm_metrics_server_address(config.env),
                    },
                )
                await run_activity(
                    activity=KedaApplyTemplatedYamlActivity,
                    arg=KedaApplyTemplatedYamlActivityModel(
                        namespace=tenant,
                        yaml_content=yaml_content,
                    ),
                )

            # deploy dicom server if enabled
            if deploy_dicom_server:
                await self._deploy_dicom_server(
                    tenant=tenant,
                    dexit=dexit,
                    config=config,
                    server_item=server_item,
                    config_dir=config_dir,
                )

            if self.is_onboarding:
                # update tenant status
                await run_activity(
                    activity=UpdateTenantStatusActivity,
                    arg=TenantCliStatus(
                        tenant_name=tenant, status=TenantStatusEnum.Provisioned, product=ProductEnum.dexit
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
                        domain_name=dexit_config.domain_name,
                        product=ProductName,
                        from_name=dexit_config.sender_name,
                        email_from=dexit_config.sender_email,
                    ),
                )

        except Exception as e:
            workflow.logger.error(f"Error in onboarding workflow: {e}")
            if self.is_onboarding:
                await run_activity(
                    activity=UpdateTenantStatusActivity,
                    arg=TenantCliStatus(
                        tenant_name=pydash.get(dexit, "tenant"),
                        status=TenantStatusEnum.ProvisioningFailed,
                        error_msg=str(e),
                        product=ProductEnum.dexit,
                    ),
                    start_to_close_timeout=timedelta(seconds=120),
                )
            raise e
