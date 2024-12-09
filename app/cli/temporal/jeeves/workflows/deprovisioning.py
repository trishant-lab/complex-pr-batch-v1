from collections.abc import Callable
from datetime import timedelta

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
from app.cli.temporal.activities.k8sService import DeleteKubernetesServiceActivity, DeleteKubernetesServiceActivityModel
from app.cli.temporal.activities.k8sconfigMap import DeleteK8sConfigMapActivity, DeleteK8sConfigMapActivityModel
from app.cli.temporal.activities.statefulSetPodCreation import (
    StatefulSetPodDeletionActivity,
    StatefulSetPodDeletionActivityModel,
)
from app.cli.temporal.activities.updateTenantStatus import TenantStatus, UpdateTenantStatusActivity
from app.cli.temporal.activities.vmPodScrapper import VMPodScrapperDeletionActivity, VMPodScrapperDeletionActivityModel
from app.cli.temporal.core.base import Workflow

from app.cli.temporal.jeeves.jeeves import JeevesSpec

with workflow.unsafe.imports_passed_through():
    from app.core.settings import get_settings, JeevesSettings


@workflow.defn(name="JeevesDeProvisioningWorkflow", sandboxed=False)
class JeevesDeProvisioningWorkflow(Workflow):
    """
    Jeeves DeBoarding Workflow
    """

    @staticmethod
    def get_activities() -> list[type[Callable]]:
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
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", workflow_input: JeevesSpec) -> str | None:
        """
        Return unique workflow id from workflow input, guarantees exactly one execution of workflow
        - Add combination of one or more fields from `workflow_input` to uniquely identify workflow
        """
        return f"de_provisioning_{workflow_input.tenant}"

    @workflow.run
    async def run(self: "Workflow", jeeves: JeevesSpec) -> None:
        """
        Entry point for workflow
        """
        jeeves_config: JeevesSettings = get_settings().jeeves

        # Wait for approval or denial
        await workflow.wait_condition(lambda: self.approved or self.deny)

        if self.deny:
            return

        tenant = pydash.get(jeeves, "tenant")

        # delete k8s service
        await workflow.execute_activity(
            DeleteKubernetesServiceActivity.defn,
            arg=DeleteKubernetesServiceActivityModel(
                namespace=tenant,
                service_name="jeeves",
            ),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=DeleteKubernetesServiceActivity.get_retry_policy(),
        )

        # delete k8s virtual service
        await workflow.execute_activity(
            DeleteKubernetesIstioVirtualServiceActivity.defn,
            arg=DeleteKubernetesIstioVirtualServiceActivityModel(
                namespace=tenant,
                service_name="jeeves-vs",
            ),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=DeleteKubernetesIstioVirtualServiceActivity.get_retry_policy(),
        )

        # delete database migration job
        await workflow.execute_activity(
            DeleteDatabaseMigrationJobActivity.defn,
            arg=DeleteDatabaseMigrationJobActivityModel(
                namespace=tenant,
                job_name="jeeves-db-schema-migration-job",
            ),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=DeleteDatabaseMigrationJobActivity.get_retry_policy(),
        )

        # delete stateful set
        await workflow.execute_activity(
            StatefulSetPodDeletionActivity.defn,
            arg=StatefulSetPodDeletionActivityModel(
                namespace=tenant,
                name="jeeves",
            ),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=StatefulSetPodDeletionActivity.get_retry_policy(),
        )

        await workflow.execute_activity(
            StatefulSetPodDeletionActivity.defn,
            arg=StatefulSetPodDeletionActivityModel(
                namespace=tenant,
                name="jeeves-worker",
            ),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=StatefulSetPodDeletionActivity.get_retry_policy(),
        )

        # delete vm pod scrapper
        await workflow.execute_activity(
            VMPodScrapperDeletionActivity.defn,
            arg=VMPodScrapperDeletionActivityModel(
                namespace=tenant,
                name="jeeves-metrics",
            ),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=VMPodScrapperDeletionActivity.get_retry_policy(),
        )

        # delete config map
        for config_map in [
            "jeeves-tenant-config",
            "jeeves-rclone-config",
            "jeeves-cli-vector-config",
            "jeeves-statestore-config",
        ]:
            await workflow.execute_activity(
                DeleteK8sConfigMapActivity.defn,
                arg=DeleteK8sConfigMapActivityModel(
                    namespace=tenant,
                    name=config_map,
                ),
                start_to_close_timeout=timedelta(seconds=120),
                retry_policy=DeleteK8sConfigMapActivity.get_retry_policy(),
            )

        # delete bucket
        bucket_name = f"{tenant}-{jeeves_config.domain_name.replace('.', '-')}"
        await workflow.execute_activity(
            DeleteCloudflareBucketActivity.defn,
            arg=DeleteCloudflareBucketActivityModel(
                bucket_name=bucket_name,
            ),
            start_to_close_timeout=DeleteCloudflareBucketActivity.get_timeout(),
            retry_policy=DeleteCloudflareBucketActivity.get_retry_policy(),
        )

        # delete dns record
        await workflow.execute_activity(
            DeleteCloudflareDNSRecordActivity.defn,
            arg=DeleteCloudflareDNSRecordActivityModel(
                domain_name=f"{tenant}.api.{jeeves_config.domain_name}",
                zone_id=jeeves_config.zone_id,
            ),
            start_to_close_timeout=DeleteCloudflareDNSRecordActivity.get_timeout(),
            retry_policy=DeleteCloudflareDNSRecordActivity.get_retry_policy(),
        )

        # update tenant status
        await workflow.execute_activity(
            UpdateTenantStatusActivity.defn,
            arg=TenantStatus(
                tenant=tenant,
                status="DeProvisioned",
            ),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
        )
