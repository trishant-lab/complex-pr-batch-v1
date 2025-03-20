from collections.abc import Callable

import pydash
from temporalio import workflow

from app.cli.temporal.activities.cloudflareSetup import (
    DeleteCloudflareBucketActivity,
    DeleteCloudflareBucketActivityModel,
    DeleteCloudflareDNSRecordActivity,
    DeleteCloudflareDNSRecordActivityModel,
    DeleteFilesFromCloudflareActivity,
)
from app.cli.temporal.activities.databaseMigrationJob import (
    DeleteDatabaseMigrationJobActivity,
    DeleteDatabaseMigrationJobActivityModel,
)
from app.cli.temporal.activities.k8sconfigMap import DeleteK8sConfigMapActivity, DeleteK8sConfigMapActivityModel
from app.cli.temporal.activities.k8sIstioVirtualService import (
    DeleteKubernetesIstioVirtualServiceActivity,
    DeleteKubernetesIstioVirtualServiceActivityModel,
)
from app.cli.temporal.activities.k8sSecret import K8sSecretDeletionActivity, K8sSecretDeletionActivityModel
from app.cli.temporal.activities.k8sService import DeleteKubernetesServiceActivity, DeleteKubernetesServiceActivityModel
from app.cli.temporal.activities.statefulSetPodCreation import (
    StatefulSetPodDeletionActivity,
    StatefulSetPodDeletionActivityModel,
)
from app.cli.temporal.activities.temporalNamespace import (
    DeleteTemporalNamespaceActivity,
    DeleteTemporalNamespaceActivityModel,
)
from app.cli.temporal.activities.updateTenantStatus import TenantStatus, UpdateTenantStatusActivity
from app.cli.temporal.activities.vmPodScrapper import VMPodScrapperDeletionActivity, VMPodScrapperDeletionActivityModel
from app.cli.temporal.core.base import Workflow
from app.cli.temporal.pricedx.models.pricedxSpec import PricedxSpec
from app.core.settings import PricedxSettings, get_settings

ProductName = "pricedx"


@workflow.defn(sandboxed=False)
class PricedxDeProvisioningWorkflow(Workflow):
    """
    Pricedx DeProvisioning Workflow
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
        ]

    @workflow.run
    async def run(self: "Workflow", pricedx: PricedxSpec) -> None:
        """
        Entry point for workflow
        """
        pricedx_config: PricedxSettings = get_settings().pricedx
        tenant = pydash.get(pricedx, "tenant")

        # Wait for approval or denial
        await workflow.wait_condition(lambda: self.approved or self.deny)

        if self.deny:
            return

        try:
            # delete k8s service
            await workflow.execute_activity(
                DeleteKubernetesServiceActivity.defn,
                arg=DeleteKubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="pricedx",
                ),
                start_to_close_timeout=DeleteKubernetesServiceActivity.get_timeout(),
                retry_policy=DeleteKubernetesServiceActivity.get_retry_policy(),
            )

            # delete k8s virtual service
            await workflow.execute_activity(
                DeleteKubernetesIstioVirtualServiceActivity.defn,
                arg=DeleteKubernetesIstioVirtualServiceActivityModel(
                    namespace=tenant,
                    service_name="pricedx-vs",
                ),
                start_to_close_timeout=DeleteKubernetesIstioVirtualServiceActivity.get_timeout(),
                retry_policy=DeleteKubernetesIstioVirtualServiceActivity.get_retry_policy(),
            )

            # delete provisioning job
            await workflow.execute_activity(
                DeleteDatabaseMigrationJobActivity.defn,
                arg=DeleteDatabaseMigrationJobActivityModel(
                    namespace=tenant,
                    job_name="pricedx-tenant-provisioning-job",
                ),
                start_to_close_timeout=DeleteDatabaseMigrationJobActivity.get_timeout(),
                retry_policy=DeleteDatabaseMigrationJobActivity.get_retry_policy(),
            )

            # delete alembic job
            await workflow.execute_activity(
                DeleteDatabaseMigrationJobActivity.defn,
                arg=DeleteDatabaseMigrationJobActivityModel(
                    namespace=tenant,
                    job_name="pricedx-tenant-alembic-job",
                ),
                start_to_close_timeout=DeleteDatabaseMigrationJobActivity.get_timeout(),
                retry_policy=DeleteDatabaseMigrationJobActivity.get_retry_policy(),
            )

            # delete stateful sets
            for stateful_set in ["pricedx", "pricedx-cli"]:
                await workflow.execute_activity(
                    StatefulSetPodDeletionActivity.defn,
                    arg=StatefulSetPodDeletionActivityModel(
                        namespace=tenant,
                        name=stateful_set,
                    ),
                    start_to_close_timeout=StatefulSetPodDeletionActivity.get_timeout(),
                    retry_policy=StatefulSetPodDeletionActivity.get_retry_policy(),
                )

            # delete config maps
            config_maps = [
                "pricedx-custom-config",
                "pricedx-env-config",
                "pricedx-tenant-config",
                "pricedx-cli-vector-config",
                "pricedx-provisioning-config",
            ]
            for config_map in config_maps:
                await workflow.execute_activity(
                    DeleteK8sConfigMapActivity.defn,
                    arg=DeleteK8sConfigMapActivityModel(
                        namespace=tenant,
                        name=config_map,
                    ),
                    start_to_close_timeout=DeleteK8sConfigMapActivity.get_timeout(),
                    retry_policy=DeleteK8sConfigMapActivity.get_retry_policy(),
                )

            # delete secrets
            secrets = [
                "tenant-cache-secret",
                "pricedx-cloudflare-r2",
            ]
            for secret in secrets:
                await workflow.execute_activity(
                    K8sSecretDeletionActivity.defn,
                    arg=K8sSecretDeletionActivityModel(
                        namespace=tenant,
                        name=secret,
                    ),
                    start_to_close_timeout=K8sSecretDeletionActivity.get_timeout(),
                    retry_policy=K8sSecretDeletionActivity.get_retry_policy(),
                )

            # delete bucket
            await workflow.execute_activity(
                DeleteCloudflareBucketActivity.defn,
                arg=DeleteCloudflareBucketActivityModel(
                    bucket_name=pricedx.cloudflare_r2_data_bucket,
                ),
                start_to_close_timeout=DeleteCloudflareBucketActivity.get_timeout(),
                retry_policy=DeleteCloudflareBucketActivity.get_retry_policy(),
            )

            # delete dns record
            await workflow.execute_activity(
                DeleteCloudflareDNSRecordActivity.defn,
                arg=DeleteCloudflareDNSRecordActivityModel(
                    domain_name=f"{tenant}.{pricedx_config.domain_name}",
                    zone_id=pricedx_config.zone_id,
                ),
                start_to_close_timeout=DeleteCloudflareDNSRecordActivity.get_timeout(),
                retry_policy=DeleteCloudflareDNSRecordActivity.get_retry_policy(),
            )

            # delete vm pod scrappers
            for scrapper in ["pricedx-metrics", "pricedx-cli-metrics"]:
                await workflow.execute_activity(
                    VMPodScrapperDeletionActivity.defn,
                    arg=VMPodScrapperDeletionActivityModel(
                        namespace=tenant,
                        name=scrapper,
                    ),
                    start_to_close_timeout=VMPodScrapperDeletionActivity.get_timeout(),
                    retry_policy=VMPodScrapperDeletionActivity.get_retry_policy(),
                )

            # delete temporal namespace
            await workflow.execute_activity(
                DeleteTemporalNamespaceActivity.defn,
                arg=DeleteTemporalNamespaceActivityModel(
                    namespace=f"pricedx_{tenant}",
                ),
                start_to_close_timeout=DeleteTemporalNamespaceActivity.get_timeout(),
                retry_policy=DeleteTemporalNamespaceActivity.get_retry_policy(),
            )


            await workflow.execute_activity(
                DeleteCloudflareBucketActivity.defn,
                arg=DeleteCloudflareBucketActivityModel(
                    bucket_name=pricedx.cloudflare_r2_ui_bucket,
                ),
                start_to_close_timeout=DeleteCloudflareBucketActivity.get_timeout(),
                retry_policy=DeleteCloudflareBucketActivity.get_retry_policy(),
            )

            # update tenant status
            await workflow.execute_activity(
                UpdateTenantStatusActivity.defn,
                arg=TenantStatus(
                    tenant_name=tenant,
                    status="DeProvisioned",
                    product=ProductName,
                ),
                start_to_close_timeout=UpdateTenantStatusActivity.get_timeout(),
                retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
            )

        except Exception as e:
            workflow.logger.error(f"Error in deprovisioning workflow: {e}")
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
