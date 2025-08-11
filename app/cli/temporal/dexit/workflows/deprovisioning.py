from collections.abc import Callable
from datetime import timedelta

import pydash
from temporalio import workflow

from app.cli.activity_util import run_activity
from app.cli.temporal.activities.cloudflare_setup import (
    DeleteCloudflareBucketActivity,
    DeleteCloudflareDNSRecordActivity,
)
from app.cli.temporal.activities.database_migration_job import (
    DeleteDatabaseMigrationJobActivity,
    DeleteDatabaseMigrationJobActivityModel,
)
from app.cli.temporal.activities.deployment import DeploymentDeletionActivity, DeploymentDeletionActivityModel
from app.cli.temporal.activities.k8s_config_map import DeleteK8sConfigMapActivity, DeleteK8sConfigMapActivityModel

from app.cli.temporal.activities.k8s_service import (
    DeleteKubernetesServiceActivity,
    DeleteKubernetesServiceActivityModel,
)
from app.cli.temporal.activities.keycloak_setup import (
    DeleteIdpFromHelpinstanceActivity,
    DeleteIdpFromHelpinstanceActivityModel,
    DeleteKeycloakClientActivity,
    DeleteKeycloakClientActivityModel,
    # DeleteKeycloakRealmActivity,
    # DeleteKeycloakRealmActivityModel,
)
from app.cli.temporal.activities.postgres_setup import (
    DeletePostgresSchemaActivity,
    DeletePostgresSchemaActivityModel,
    DeletePostgresUserActivity,
    DeletePostgresUserActivityModel,
    DeleteSupavisorTenantActivity,
    DeleteSupavisorTenantActivityModel,
    RevokeAllPrivilegesOnTableActivity,
    RevokeKeycloakUserMappingActivity,
    RevokeMatomoUserMappingActivity,
    KeycloakUserMappingActivityModel,
    MatomoUserMappingActivityModel,
)

# from app.cli.temporal.activities.temporal_namespace import (
#     DeleteTemporalNamespaceActivity,
#     DeleteTemporalNamespaceActivityModel,
# )
from app.cli.temporal.activities.k8s_istio_virtual_service import (
    DeleteKubernetesIstioVirtualServiceActivity,
    DeleteKubernetesIstioVirtualServiceActivityModel,
)
from app.cli.temporal.activities.update_tenant_status import TenantCliStatus, UpdateTenantStatusActivity
from app.cli.temporal.activities.vm_pod_scrapper import (
    VMPodScrapperDeletionActivity,
    VMPodScrapperDeletionActivityModel,
)
from app.cli.temporal.core.base import Workflow
from app.cli.temporal.models.cloudflare import (
    DeleteCloudflareBucketActivityModel,
    DeleteCloudflareDNSRecordActivityModel,
)
from app.cli.temporal.models.deboard import DeboardWorkflowInput
from app.core.settings import DexitSettings, get_settings
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum

ProductName = "dexit"


@workflow.defn(name="DexitDeProvisioningWorkflow")
class DexitDeProvisioningWorkflow(Workflow):
    """
    Dexit DeBoarding Workflow
    """

    def __init__(self: "Workflow") -> None:
        self.approved: bool = False
        self.denied: bool = False

    @staticmethod
    def get_activities() -> list[type[Callable]]:
        """
        Return list of activities used in the workflow
        """
        return [
            # DeleteTemporalNamespaceActivity.defn,
            DeleteKubernetesServiceActivity.defn,
            VMPodScrapperDeletionActivity.defn,
            DeleteK8sConfigMapActivity.defn,
            DeleteCloudflareBucketActivity.defn,
            DeleteCloudflareDNSRecordActivity.defn,
            DeleteKubernetesIstioVirtualServiceActivity.defn,
            UpdateTenantStatusActivity.defn,
            DeleteSupavisorTenantActivity.defn,
            DeletePostgresUserActivity.defn,
            DeletePostgresSchemaActivity.defn,
            DeleteKeycloakClientActivity.defn,
            # DeleteKeycloakRealmActivity.defn,
            DeleteIdpFromHelpinstanceActivity.defn,
            DeploymentDeletionActivity.defn,
            DeleteDatabaseMigrationJobActivity.defn,
            RevokeAllPrivilegesOnTableActivity.defn,
            RevokeKeycloakUserMappingActivity.defn,
            RevokeMatomoUserMappingActivity.defn,
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", workflow_input: DeboardWorkflowInput) -> str | None:
        """
        Return unique workflow id from workflow input, guarantees exactly one execution of workflow
        - Add combination of one or more fields from `workflow_input` to uniquely identify workflow
        """
        return f"dexit_deprovisioning_workflow_{pydash.get(workflow_input, 'tenant_name')}"

    @workflow.run
    async def run(self: "Workflow", dexit: DeboardWorkflowInput) -> None:
        """
        Entry point for workflow
        """
        dexit_config: DexitSettings = get_settings().dexit

        # Wait for approval or denial
        await workflow.wait_condition(lambda: self.approved or self.denied)

        if self.denied:
            return

        tenant = pydash.get(dexit, "tenant_name")

        try:
            # delete k8s service
            await run_activity(
                activity=DeleteKubernetesServiceActivity,
                arg=DeleteKubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="dexit",
                ),
                start_to_close_timeout=timedelta(seconds=120),
            )

            await run_activity(
                activity=DeleteKubernetesServiceActivity,
                arg=DeleteKubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="dexit-dicom",
                ),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # delete k8s virtual service
            await run_activity(
                activity=DeleteKubernetesIstioVirtualServiceActivity,
                arg=DeleteKubernetesIstioVirtualServiceActivityModel(
                    namespace=tenant,
                    service_name="dexit-vs",
                ),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # delete vm pod scrapper
            await run_activity(
                activity=VMPodScrapperDeletionActivity,
                arg=VMPodScrapperDeletionActivityModel(
                    namespace=tenant,
                    name="dexit-metrics",
                ),
                start_to_close_timeout=timedelta(seconds=120),
            )
            dexit_worker_pods = ["dexit-worker-all", "dexit-worker-dsl", "dexit-worker-dslp", "dexit-worker-event"]
            for pod in dexit_worker_pods:
                await run_activity(
                    activity=VMPodScrapperDeletionActivity,
                    arg=VMPodScrapperDeletionActivityModel(
                        namespace=tenant,
                        name=f"{pod}-metrics",
                    ),
                    start_to_close_timeout=timedelta(seconds=120),
                )

            # delete deployment
            await run_activity(
                activity=DeploymentDeletionActivity,
                arg=DeploymentDeletionActivityModel(
                    namespace=tenant,
                    name="dexit",
                ),
                start_to_close_timeout=timedelta(seconds=120),
            )

            await run_activity(
                activity=DeploymentDeletionActivity,
                arg=DeploymentDeletionActivityModel(
                    namespace=tenant,
                    name="dexit-dicom",
                ),
                start_to_close_timeout=timedelta(seconds=120),
            )

            for pod in dexit_worker_pods:
                await run_activity(
                    activity=DeploymentDeletionActivity,
                    arg=DeploymentDeletionActivityModel(
                        namespace=tenant,
                        name=pod,
                    ),
                    start_to_close_timeout=timedelta(seconds=120),
                )

            # delete config map
            for config_map in [
                "dexit-env-config",
                "dexit-tenant-config",
                "dexit-mlops-config",
                "dexit-dicom-config",
                "dexit-cli-vector-config",
            ]:
                await run_activity(
                    activity=DeleteK8sConfigMapActivity,
                    arg=DeleteK8sConfigMapActivityModel(
                        namespace=tenant,
                        name=config_map,
                    ),
                    start_to_close_timeout=timedelta(seconds=120),
                )

            # await run_activity(
            #     activity=DeleteTemporalNamespaceActivity,
            #     arg=DeleteTemporalNamespaceActivityModel(
            #         namespace=f"dexit_{tenant}",
            #     ),
            #     start_to_close_timeout=timedelta(seconds=120),
            # )

            # delete database migration job
            await run_activity(
                activity=DeleteDatabaseMigrationJobActivity,
                arg=DeleteDatabaseMigrationJobActivityModel(
                    namespace=tenant,
                    job_name="dexit-atlas-migration-job",
                ),
                start_to_close_timeout=timedelta(seconds=120),
            )

            await run_activity(
                activity=DeleteSupavisorTenantActivity,
                arg=DeleteSupavisorTenantActivityModel(
                    supavisor_tenant_name=f"dexit_{tenant}",
                ),
                start_to_close_timeout=timedelta(seconds=120),
            )

            await run_activity(
                activity=DeletePostgresUserActivityModel,
                arg=RevokeAllPrivilegesOnTableActivity(
                    username=f"dexit_{tenant}",
                    database_name="dexit",
                ),
            )

            await run_activity(
                activity=DeletePostgresUserActivityModel,
                arg=RevokeAllPrivilegesOnTableActivity(
                    username=f"dexit_dicom_{tenant}",
                    database_name=f"dexit_dicom_{tenant}",
                ),
            )

            await run_activity(
                activity=RevokeKeycloakUserMappingActivity,
                arg=KeycloakUserMappingActivityModel(
                    username=f"dexit_{tenant}",
                    database_name="dexit",
                ),
            )

            await run_activity(
                activity=RevokeKeycloakUserMappingActivity,
                arg=KeycloakUserMappingActivityModel(
                    username=f"dexit_dicom_{tenant}",
                    database_name=f"dexit_dicom_{tenant}",
                ),
            )

            await run_activity(
                activity=RevokeMatomoUserMappingActivity,
                arg=MatomoUserMappingActivityModel(
                    username=f"dexit_{tenant}",
                    database_name="dexit",
                ),
            )

            await run_activity(
                activity=RevokeMatomoUserMappingActivity,
                arg=MatomoUserMappingActivityModel(
                    username=f"dexit_dicom_{tenant}",
                    database_name=f"dexit_dicom_{tenant}",
                ),
            )

            await run_activity(
                activity=DeletePostgresUserActivity,
                arg=DeletePostgresUserActivityModel(
                    username=f"dexit_{tenant}",
                    database_name="dexit",
                ),
                start_to_close_timeout=timedelta(seconds=120),
            )

            await run_activity(
                activity=DeletePostgresUserActivity,
                arg=DeletePostgresUserActivityModel(
                    username=f"dexit_dicom_{tenant}",  # From onboarding line 257
                    database_name=f"dexit_dicom_{tenant}",  # From onboarding line 228
                ),
                start_to_close_timeout=timedelta(seconds=120),
            )

            await run_activity(
                activity=DeletePostgresSchemaActivity,
                arg=DeletePostgresSchemaActivityModel(
                    schema_name=tenant,
                    database_name="dexit",
                ),
                start_to_close_timeout=timedelta(seconds=120),
            )

            await run_activity(
                activity=DeletePostgresSchemaActivity,
                arg=DeletePostgresSchemaActivityModel(
                    schema_name=tenant,
                    database_name=f"{ProductName}_dicom_{tenant}",
                ),
                start_to_close_timeout=timedelta(seconds=120),
            )

            await run_activity(
                activity=DeleteKeycloakClientActivity,
                arg=DeleteKeycloakClientActivityModel(
                    client_name="dexit",
                    realm_name=tenant,
                ),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # await run_activity(
            #     activity=DeleteKeycloakRealmActivity,
            #     arg=DeleteKeycloakRealmActivityModel(
            #         client_name="dexit",
            #         realm_name=tenant,
            #     ),
            #     start_to_close_timeout=timedelta(seconds=120),
            # )

            await run_activity(
                activity=DeleteIdpFromHelpinstanceActivity,
                arg=DeleteIdpFromHelpinstanceActivityModel(
                    tenant=tenant,
                    is_prod=True,
                ),
                start_to_close_timeout=timedelta(seconds=120),
            )

            # delete bucket
            bucket_name = f"{tenant}-{dexit_config.domain_name.replace('.', '-')}"
            await run_activity(
                activity=DeleteCloudflareBucketActivity,
                arg=DeleteCloudflareBucketActivityModel(
                    bucket_name=bucket_name,
                ),
            )

            # delete dns record
            await run_activity(
                activity=DeleteCloudflareDNSRecordActivity,
                arg=DeleteCloudflareDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{dexit_config.domain_name}",
                    zone_id=dexit_config.zone_id,
                ),
            )

            # update tenant status to success
            await run_activity(
                activity=UpdateTenantStatusActivity,
                arg=TenantCliStatus(
                    tenant_name=tenant,
                    status=TenantStatusEnum.DeProvisioned,
                    product=ProductEnum.dexit,
                ),
                start_to_close_timeout=timedelta(seconds=120),
            )

        except Exception as e:
            workflow.logger.error(f"Error in deprovisioning workflow: {e}")
            await run_activity(
                activity=UpdateTenantStatusActivity,
                arg=TenantCliStatus(
                    tenant_name=tenant,
                    status=TenantStatusEnum.DeprovisioningFailed,
                    error_msg=str(e),
                    product=ProductEnum.dexit,
                ),
            )
            raise e

    @workflow.signal
    async def approve(self: "Workflow") -> None:
        """
        Approve the workflow
        """
        self.approved = True

    @workflow.signal
    async def decline(self: "Workflow") -> None:
        """
        Deny the workflow
        """
        self.denied = True
