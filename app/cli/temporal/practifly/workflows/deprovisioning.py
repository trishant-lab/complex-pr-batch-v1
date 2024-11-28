from collections.abc import Callable

import pydash
from temporalio import workflow

from app.cli.temporal.activities.cloudflareSetup import (
    DeleteCloudflareBucketActivity,
    DeleteCloudflareBucketActivityModel,
    DeleteCloudflareDNSRecordActivity,
    DeleteCloudflareDNSRecordActivityModel,
)
from app.cli.temporal.activities.databaseMigrationJob import (
    DeleteDatabaseMigrationJobActivity,
    DeleteDatabaseMigrationJobActivityModel,
)
from app.cli.temporal.activities.k8sIstioVirtualService import (
    DeleteKubernetesIstioVirtualServiceActivity,
    DeleteKubernetesIstioVirtualServiceActivityModel,
)
from app.cli.temporal.activities.cloudflareSetup import (
    DeleteFilesFromCloudflareActivity,
    DeleteFilesFromCloudflareActivityModel,
)
from app.cli.temporal.activities.k8sService import DeleteKubernetesServiceActivity, DeleteKubernetesServiceActivityModel
from app.cli.temporal.activities.k8sconfigMap import DeleteK8sConfigMapActivity, DeleteK8sConfigMapActivityModel
from app.cli.temporal.activities.k8sSecret import K8sSecretDeletionActivity, K8sSecretDeletionActivityModel
from app.cli.temporal.activities.statefulSetPodCreation import (
    StatefulSetPodDeletionActivity,
    StatefulSetPodDeletionActivityModel,
)
from app.cli.temporal.activities.pvcSetup import PVCDeletionActivity, PVCDeletionActivityModel
from app.cli.temporal.activities.updateTenantStatus import TenantStatus, UpdateTenantStatusActivity
from app.cli.temporal.activities.vmPodScrapper import VMPodScrapperDeletionActivity, VMPodScrapperDeletionActivityModel
from app.cli.temporal.activities.temporalNamespace import (
    DeleteTemporalNamespaceActivity,
    DeleteTemporalNamespaceActivityModel,
)
from app.cli.temporal.core.base import Workflow
from app.cli.temporal.practifly.models.practiflySpec import PractiflySpec

with workflow.unsafe.imports_passed_through():
    from app.core.settings import get_settings, PractiflySettings, AppSettings


@workflow.defn(name="PractiflyDeProvisioningWorkflow", sandboxed=False)
class PractiflyDeProvisioningWorkflow(Workflow):
    """
    Practifly DeProvisioning Workflow
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
            DeleteK8sConfigMapActivity.defn,
            DeleteCloudflareBucketActivity.defn,
            DeleteCloudflareDNSRecordActivity.defn,
            UpdateTenantStatusActivity.defn,
            DeleteKubernetesIstioVirtualServiceActivity.defn,
            DeleteDatabaseMigrationJobActivity.defn,
            PVCDeletionActivity.defn,
        ]

    @workflow.run
    async def run(self: "Workflow", practifly: PractiflySpec) -> None:
        """
        Entry point for workflow
        """
        config: AppSettings = get_settings()
        practifly_config: PractiflySettings = get_settings().practifly
        tenant = pydash.get(practifly, "tenant")

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
                    service_name="practifly",
                ),
                start_to_close_timeout=DeleteKubernetesServiceActivity.get_timeout(),
                retry_policy=DeleteKubernetesServiceActivity.get_retry_policy(),
            )

            # delete k8s virtual service
            await workflow.execute_activity(
                DeleteKubernetesIstioVirtualServiceActivity.defn,
                arg=DeleteKubernetesIstioVirtualServiceActivityModel(
                    namespace=tenant,
                    service_name="practifly-vs",
                ),
                start_to_close_timeout=DeleteKubernetesIstioVirtualServiceActivity.get_timeout(),
                retry_policy=DeleteKubernetesIstioVirtualServiceActivity.get_retry_policy(),
            )

            # delete database migration job
            await workflow.execute_activity(
                DeleteDatabaseMigrationJobActivity.defn,
                arg=DeleteDatabaseMigrationJobActivityModel(
                    namespace=tenant,
                    job_name="practifly-tenant-alembic-job",
                ),
                start_to_close_timeout=DeleteDatabaseMigrationJobActivity.get_timeout(),
                retry_policy=DeleteDatabaseMigrationJobActivity.get_retry_policy(),
            )

            # delete stateful sets
            for stateful_set in ["practifly", "practifly-cli"]:
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
                "practifly-common-config",
                "practifly-env-config",
                "practifly-tenant-config",
                "practifly-cli-vector-config",
                "practifly-provisioning-config",
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
            secrets = ["registrycred", "cache-secret", "tenant-cache-secret", "postgres-secret"]
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
            bucket_name = f"{tenant}.{practifly_config.domain_name}"
            bucket_name = bucket_name.replace(".", "-")
            await workflow.execute_activity(
                DeleteCloudflareBucketActivity.defn,
                arg=DeleteCloudflareBucketActivityModel(
                    bucket_name=bucket_name,
                ),
                start_to_close_timeout=DeleteCloudflareBucketActivity.get_timeout(),
                retry_policy=DeleteCloudflareBucketActivity.get_retry_policy(),
            )

            image_tag = "production" if config.env == "production" else "sprint"
            # delete files from cloudflare
            await workflow.execute_activity(
                DeleteFilesFromCloudflareActivity.defn,
                arg=DeleteFilesFromCloudflareActivityModel(
                    bucket_name=bucket_name,
                    dest_dir=f"{image_tag}/practifly-web-core",
                    bundle_name="release.zip",
                    tenant=tenant,
                ),
                start_to_close_timeout=DeleteFilesFromCloudflareActivity.get_timeout(),
                retry_policy=DeleteFilesFromCloudflareActivity.get_retry_policy(),
            )

            # delete pvc
            await workflow.execute_activity(
                PVCDeletionActivity.defn,
                arg=PVCDeletionActivityModel(
                    tenant=tenant,
                    pvc_name="practifly-pvc",
                ),
                start_to_close_timeout=PVCDeletionActivity.get_timeout(),
                retry_policy=PVCDeletionActivity.get_retry_policy(),
            )

            # delete dns record
            await workflow.execute_activity(
                DeleteCloudflareDNSRecordActivity.defn,
                arg=DeleteCloudflareDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{practifly_config.domain_name}",
                    zone_id=practifly_config.zone_id,
                ),
                start_to_close_timeout=DeleteCloudflareDNSRecordActivity.get_timeout(),
                retry_policy=DeleteCloudflareDNSRecordActivity.get_retry_policy(),
            )

            # delete vm pod scrappers
            for scrapper in ["practifly-metrics", "practifly-cli-metrics"]:
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
                    namespace=f"practifly_{tenant}",
                ),
                start_to_close_timeout=DeleteTemporalNamespaceActivity.get_timeout(),
                retry_policy=DeleteTemporalNamespaceActivity.get_retry_policy(),
            )

            # update tenant status
            await workflow.execute_activity(
                UpdateTenantStatusActivity.defn,
                arg=TenantStatus(
                    tenant_name=tenant,
                    status="DeProvisioned",
                    product="practifly",
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
                    product="practifly",
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
