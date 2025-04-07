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
from app.cli.temporal.activities.stateful_set_pod_creation import (
    StatefulSetPodDeletionActivity,
    StatefulSetPodDeletionActivityModel,
)
from app.cli.temporal.activities.temporal_namespace import (
    DeleteTemporalNamespaceActivity,
    DeleteTemporalNamespaceActivityModel,
)
from app.cli.temporal.activities.update_tenant_status import TenantCliStatus, UpdateTenantStatusActivity
from app.cli.temporal.activities.veritable_novu_setup import VeritableNovuDeProvisionActivity
from app.cli.temporal.activities.vm_pod_scrapper import (
    VMPodScrapperDeletionActivity,
    VMPodScrapperDeletionActivityModel,
)
from app.cli.temporal.core.base import Workflow
from app.cli.temporal.models.cloudflare import (
    DeleteCloudflareBucketActivityModel,
    DeleteCloudflareDNSRecordActivityModel,
)
from app.cli.temporal.veritable.models.veritable_spec import VeritableSpec
from app.core.settings import VeritableSettings, get_settings
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum

ProductName = "veritable"


@workflow.defn(sandboxed=False)
class VeritableDeProvisioningWorkflow(Workflow):
    """
    Veritable DeProvisioning Workflow
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
            DeleteKubernetesServiceActivity.defn,
            StatefulSetPodDeletionActivity.defn,
            VMPodScrapperDeletionActivity.defn,
            DeleteTemporalNamespaceActivity.defn,
            DeleteK8sConfigMapActivity.defn,
            K8sSecretDeletionActivity.defn,
            DeleteCloudflareBucketActivity.defn,
            DeleteCloudflareDNSRecordActivity.defn,
            DeleteFilesFromCloudflareActivity.defn,
            UpdateTenantStatusActivity.defn,
            DeleteKubernetesIstioVirtualServiceActivity.defn,
            DeleteDatabaseMigrationJobActivity.defn,
            VeritableNovuDeProvisionActivity.defn,
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", veritable: VeritableSpec) -> str:
        """
        Get the workflow id
        """
        return f"veritable_deprovisioning_workflow_{pydash.get(veritable, 'tenant')}"

    @workflow.run
    async def run(self: "Workflow", veritable: VeritableSpec) -> None:
        """
        Entry point for workflow
        """
        veritable_config: VeritableSettings = get_settings().veritable
        tenant = pydash.get(veritable, "tenant")

        # Wait for approval or denial
        await workflow.wait_condition(lambda: self.approved or self.deny)

        if self.deny:
            return

        try:
            # delete k8s service
            await run_activity(
                activity=DeleteKubernetesServiceActivity,
                arg=DeleteKubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="veritable",
                ),
            )

            # delete k8s virtual service
            await run_activity(
                activity=DeleteKubernetesIstioVirtualServiceActivity,
                arg=DeleteKubernetesIstioVirtualServiceActivityModel(
                    namespace=tenant,
                    service_name="veritable-vs",
                ),
            )

            # delete provisioning job
            await run_activity(
                activity=DeleteDatabaseMigrationJobActivity,
                arg=DeleteDatabaseMigrationJobActivityModel(
                    namespace=tenant,
                    job_name="veritable-tenant-provisioning-job",
                ),
            )

            # delete alembic job
            await run_activity(
                activity=DeleteDatabaseMigrationJobActivity,
                arg=DeleteDatabaseMigrationJobActivityModel(
                    namespace=tenant,
                    job_name="veritable-tenant-alembic-job",
                ),
            )

            # delete stateful sets
            for stateful_set in ["veritable", "veritable-cli"]:
                await run_activity(
                    activity=StatefulSetPodDeletionActivity,
                    arg=StatefulSetPodDeletionActivityModel(
                        namespace=tenant,
                        name=stateful_set,
                    ),
                )

            # delete config maps
            config_maps = [
                "veritable-custom-config",
                "veritable-env-config",
                "veritable-tenant-config",
                "veritable-cli-vector-config",
                "veritable-provisioning-config",
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
            secrets = [
                "tenant-cache-secret",
                "veritable-novu",
                "veritable-cloudflare-r2",
            ]
            for secret in secrets:
                await run_activity(
                    activity=K8sSecretDeletionActivity,
                    arg=K8sSecretDeletionActivityModel(
                        namespace=tenant,
                        name=secret,
                    ),
                )

            # delete bucket
            await run_activity(
                activity=DeleteCloudflareBucketActivity,
                arg=DeleteCloudflareBucketActivityModel(
                    bucket_name=veritable.cloudflare_r2_data_bucket,
                ),
            )

            # delete dns record
            await run_activity(
                activity=DeleteCloudflareDNSRecordActivity,
                arg=DeleteCloudflareDNSRecordActivityModel(
                    domain_name=f"{tenant}.{veritable_config.domain_name}",
                    zone_id=veritable_config.zone_id,
                ),
            )

            # delete vm pod scrappers
            for scrapper in ["veritable-metrics", "veritable-cli-metrics"]:
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
                    namespace=f"veritable_{tenant}",
                ),
            )

            await run_activity(
                activity=VeritableNovuDeProvisionActivity,
                arg=veritable,
            )

            await run_activity(
                activity=DeleteCloudflareBucketActivity,
                arg=DeleteCloudflareBucketActivityModel(
                    bucket_name=veritable.cloudflare_r2_ui_bucket,
                ),
            )

            # update tenant status
            await run_activity(
                activity=UpdateTenantStatusActivity,
                arg=TenantCliStatus(
                    tenant_name=tenant,
                    status=TenantStatusEnum.DeProvisioned,
                    product=ProductEnum.veritable,
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
                    product=ProductEnum.veritable,
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
    async def deny(self: "Workflow") -> None:
        """
        Deny the workflow
        """
        self.deny = True
