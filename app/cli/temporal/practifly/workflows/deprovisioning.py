from collections.abc import Callable

import pydash
from temporalio import workflow

from app.cli.activity_util import run_activity
from app.cli.temporal.activities.cloudflare_setup import (
    DeleteCloudflareBucketActivity,
    DeleteCloudflareDNSRecordActivity,
    DeleteFilesFromCloudflareActivity,
)
from app.cli.temporal.activities.database_migration_job import (
    DeleteDatabaseMigrationJobActivity,
    DeleteDatabaseMigrationJobActivityModel,
)
from app.cli.temporal.activities.k8s_config_map import DeleteK8sConfigMapActivity, DeleteK8sConfigMapActivityModel
from app.cli.temporal.activities.k8s_istio_virtual_service import (
    DeleteKubernetesIstioVirtualServiceActivity,
    DeleteKubernetesIstioVirtualServiceActivityModel,
)
from app.cli.temporal.activities.k8s_secret import K8sSecretDeletionActivity, K8sSecretDeletionActivityModel
from app.cli.temporal.activities.k8s_service import (
    DeleteKubernetesServiceActivity,
    DeleteKubernetesServiceActivityModel,
)
from app.cli.temporal.activities.pvc_setup import PVCDeletionActivity, PVCDeletionActivityModel
from app.cli.temporal.activities.stateful_set_pod_creation import (
    StatefulSetPodDeletionActivity,
    StatefulSetPodDeletionActivityModel,
)
from app.cli.temporal.activities.temporal_namespace import (
    DeleteTemporalNamespaceActivity,
    DeleteTemporalNamespaceActivityModel,
)
from app.cli.temporal.activities.tenant_crd import TenantCrdDeletionActivity, TenantCrdDeletionActivityModel
from app.cli.temporal.activities.update_tenant_status import TenantCliStatus, UpdateTenantStatusActivity
from app.cli.temporal.activities.vm_pod_scrapper import (
    VMPodScrapperDeletionActivity,
    VMPodScrapperDeletionActivityModel,
)
from app.cli.temporal.core.base import Workflow
from app.cli.temporal.models.cloudflare import (
    DeleteCloudflareBucketActivityModel,
    DeleteCloudflareDNSRecordActivityModel,
    DeleteFilesFromCloudflareActivityModel,
)
from app.cli.temporal.models.deboard import DeboardWorkflowInput
from app.core.settings import AppSettings, PractiflySettings, get_settings
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum


@workflow.defn(sandboxed=False)
class PractiflyDeProvisioningWorkflow(Workflow):
    """
    Practifly DeProvisioning Workflow
    """

    def __init__(self: "Workflow") -> None:
        self.approved: bool = False
        self.denied: bool = False

    @staticmethod
    def get_activities() -> list[type[Callable]]:  # type: ignore
        """
        Return list of activities used in the workflow
        """
        return [
            DeleteKubernetesServiceActivity.defn,
            StatefulSetPodDeletionActivity.defn,
            VMPodScrapperDeletionActivity.defn,
            DeleteK8sConfigMapActivity.defn,
            DeleteCloudflareBucketActivity.defn,
            DeleteCloudflareDNSRecordActivity.defn,
            UpdateTenantStatusActivity.defn,
            DeleteKubernetesIstioVirtualServiceActivity.defn,
            DeleteDatabaseMigrationJobActivity.defn,
            PVCDeletionActivity.defn,
            K8sSecretDeletionActivity.defn,
            DeleteFilesFromCloudflareActivity.defn,
            DeleteTemporalNamespaceActivity.defn,
            TenantCrdDeletionActivity.defn,
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", practifly: DeboardWorkflowInput) -> str:
        """
        Return workflow id
        """
        return f"practifly_deprovisioning_workflow_{pydash.get(practifly, 'tenant_id')}"

    @workflow.run
    async def run(self: "Workflow", practifly: DeboardWorkflowInput) -> None:
        """
        Entry point for workflow
        """
        config: AppSettings = get_settings()
        practifly_config: PractiflySettings = config.practifly
        tenant = pydash.get(practifly, "tenant_name")

        # Wait for approval or denial
        await workflow.wait_condition(lambda: self.approved or self.denied)

        if self.denied:
            return

        try:
            # delete k8s service
            await run_activity(
                activity=DeleteKubernetesServiceActivity,
                arg=DeleteKubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="practifly",
                ),
            )

            # delete k8s virtual service
            await run_activity(
                activity=DeleteKubernetesIstioVirtualServiceActivity,
                arg=DeleteKubernetesIstioVirtualServiceActivityModel(
                    namespace=tenant,
                    service_name="practifly-vs",
                ),
            )

            # delete database migration job
            await run_activity(
                activity=DeleteDatabaseMigrationJobActivity,
                arg=DeleteDatabaseMigrationJobActivityModel(
                    namespace=tenant,
                    job_name="practifly-tenant-alembic-job",
                ),
            )

            # delete provisioning job
            await run_activity(
                activity=DeleteDatabaseMigrationJobActivity,
                arg=DeleteDatabaseMigrationJobActivityModel(
                    namespace=tenant,
                    job_name="practifly-tenant-provisioning-job",
                ),
            )

            # delete database migration job
            await run_activity(
                activity=DeleteDatabaseMigrationJobActivity,
                arg=DeleteDatabaseMigrationJobActivityModel(
                    namespace=tenant,
                    job_name="practifly-tenant-deployment-job",
                ),
            )

            # delete stateful sets
            for stateful_set in ["practifly", "practifly-cli"]:
                await run_activity(
                    activity=StatefulSetPodDeletionActivity,
                    arg=StatefulSetPodDeletionActivityModel(
                        namespace=tenant,
                        name=stateful_set,
                    ),
                )

            # delete config maps
            config_maps = [
                "practifly-common-config",
                "practifly-env-config",
                "practifly-tenant-config",
                "practifly-cli-vector-config",
                "practifly-provisioning-config",
            ]
            for config_map in config_maps:
                await run_activity(
                    activity=DeleteK8sConfigMapActivity,
                    arg=DeleteK8sConfigMapActivityModel(
                        namespace=tenant,
                        name=config_map,
                    ),
                )

            # delete secrets
            secrets = ["practifly-postgres", "practifly-redis"]
            for secret in secrets:
                await run_activity(
                    activity=K8sSecretDeletionActivity,
                    arg=K8sSecretDeletionActivityModel(
                        namespace=tenant,
                        name=secret,
                    ),
                )

            # delete bucket
            bucket_name = f"{tenant}.{practifly_config.domain_name}"
            bucket_name = bucket_name.replace(".", "-")

            # delete dns record
            await run_activity(
                activity=DeleteCloudflareDNSRecordActivity,
                arg=DeleteCloudflareDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{practifly_config.domain_name}",
                    zone_id=practifly_config.zone_id,
                ),
            )

            # delete files from cloudflare
            await run_activity(
                activity=DeleteFilesFromCloudflareActivity,
                arg=DeleteFilesFromCloudflareActivityModel(
                    bucket_name=bucket_name,
                    tenant=tenant,
                ),
            )

            # delete bucket
            await run_activity(
                activity=DeleteCloudflareBucketActivity,
                arg=DeleteCloudflareBucketActivityModel(
                    bucket_name=bucket_name,
                ),
            )

            # delete pvc
            await run_activity(
                activity=PVCDeletionActivity,
                arg=PVCDeletionActivityModel(
                    tenant=tenant,
                    pvc_name="practifly-pvc",
                ),
            )

            # delete vm pod scrappers
            for scrapper in ["practifly-metrics", "practifly-cli-metrics"]:
                await run_activity(
                    activity=VMPodScrapperDeletionActivity,
                    arg=VMPodScrapperDeletionActivityModel(
                        namespace=tenant,
                        name=scrapper,
                    ),
                )

            # delete temporal namespace
            await run_activity(
                activity=DeleteTemporalNamespaceActivity,
                arg=DeleteTemporalNamespaceActivityModel(
                    namespace=f"practifly_{tenant}",
                ),
            )

            # update tenant status
            await run_activity(
                activity=UpdateTenantStatusActivity,
                arg=TenantCliStatus(
                    tenant_name=tenant,
                    status=TenantStatusEnum.DeProvisioned,
                    product=ProductEnum.practifly,
                ),
            )

            await run_activity(
                activity=TenantCrdDeletionActivity,
                arg=TenantCrdDeletionActivityModel(
                    tenant=tenant,
                    kind="PractiflyTenant",
                    product="practifly",
                ),
            )

        except Exception as e:
            workflow.logger.error(f"Error in deprovisioning workflow: {e}")
            await run_activity(
                activity=UpdateTenantStatusActivity,
                arg=TenantCliStatus(
                    tenant_name=tenant,
                    status=TenantStatusEnum.DeprovisioningFailed,
                    error_msg=str(e),
                    product=ProductEnum.practifly,
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
