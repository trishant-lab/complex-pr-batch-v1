from collections.abc import Callable
from datetime import timedelta

import pydash
from temporalio import workflow

from app.cli.activity_util import run_activity
from app.cli.temporal.activities.chatwoot_setup import DeleteChatwootAccountActivity, DeleteChatwootAccountActivityModel
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
from app.cli.temporal.activities.k8s_istio_virtual_service import (
    DeleteKubernetesIstioVirtualServiceActivity,
    DeleteKubernetesIstioVirtualServiceActivityModel,
)
from app.cli.temporal.activities.k8s_service import (
    DeleteKubernetesServiceActivity,
    DeleteKubernetesServiceActivityModel,
)
from app.cli.temporal.activities.keycloak_setup import (
    DeleteIdpFromHelpinstanceActivity,
    DeleteIdpFromHelpinstanceActivityModel,
    DeleteKeycloakClientActivity,
    DeleteKeycloakClientActivityModel,
    DeleteKeycloakRealmActivity,
    DeleteKeycloakRealmActivityModel,
)
from app.cli.temporal.activities.postgres_setup import (
    DeletePostgresSchemaActivity,
    DeletePostgresSchemaActivityModel,
    DeletePostgresUserActivity,
    DeletePostgresUserActivityModel,
    DeleteSupavisorTenantActivity,
    DeleteSupavisorTenantActivityModel,
)
from app.cli.temporal.activities.redis import RedisDeleteNamespaceActivity, RedisDeleteNamespaceActivityModel
from app.cli.temporal.activities.temporal_namespace import (
    DeleteTemporalNamespaceActivity,
    DeleteTemporalNamespaceActivityModel,
)
from app.cli.temporal.activities.update_tenant_status import TenantCliStatus, UpdateTenantStatusActivity
from app.cli.temporal.activities.vespa_job import VespaDeleteActivity, VespaDeleteActivityModel
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
from app.core.settings import JeevesSettings, get_settings
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum


@workflow.defn(name="JeevesDeProvisioningWorkflow")
class JeevesDeProvisioningWorkflow(Workflow):
    """
    Jeeves DeBoarding Workflow
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
            VespaDeleteActivity.defn,
            DeleteTemporalNamespaceActivity.defn,
            DeleteKubernetesServiceActivity.defn,
            VMPodScrapperDeletionActivity.defn,
            DeleteK8sConfigMapActivity.defn,
            DeleteCloudflareBucketActivity.defn,
            DeleteCloudflareDNSRecordActivity.defn,
            UpdateTenantStatusActivity.defn,
            DeleteKubernetesIstioVirtualServiceActivity.defn,
            DeleteDatabaseMigrationJobActivity.defn,
            DeleteSupavisorTenantActivity.defn,
            DeletePostgresUserActivity.defn,
            DeletePostgresSchemaActivity.defn,
            DeleteChatwootAccountActivity.defn,
            DeleteKeycloakClientActivity.defn,
            DeleteKeycloakRealmActivity.defn,
            DeleteIdpFromHelpinstanceActivity.defn,
            RedisDeleteNamespaceActivity.defn,
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", workflow_input: DeboardWorkflowInput) -> str | None:
        """
        Return unique workflow id from workflow input, guarantees exactly one execution of workflow
        - Add combination of one or more fields from `workflow_input` to uniquely identify workflow
        """
        return f"de_provisioning_{pydash.get(workflow_input, 'tenant_id')}"

    @workflow.run
    async def run(self: "Workflow", jeeves: DeboardWorkflowInput) -> None:
        """
        Entry point for workflow
        """
        jeeves_config: JeevesSettings = get_settings().jeeves

        # Wait for approval or denial
        await workflow.wait_condition(lambda: self.approved or self.denied)

        if self.denied:
            return

        tenant = pydash.get(jeeves, "tenant_name")

        # delete k8s service
        await run_activity(
            activity=DeleteKubernetesServiceActivity,
            arg=DeleteKubernetesServiceActivityModel(
                namespace=tenant,
                service_name="jeeves",
            ),
            start_to_close_timeout=timedelta(seconds=120),
        )

        # delete k8s virtual service
        await run_activity(
            activity=DeleteKubernetesIstioVirtualServiceActivity,
            arg=DeleteKubernetesIstioVirtualServiceActivityModel(
                namespace=tenant,
                service_name="jeeves-vs",
            ),
            start_to_close_timeout=timedelta(seconds=120),
        )

        # delete vm pod scrapper
        await run_activity(
            activity=VMPodScrapperDeletionActivity,
            arg=VMPodScrapperDeletionActivityModel(
                namespace=tenant,
                name="jeeves-metrics",
            ),
            start_to_close_timeout=timedelta(seconds=120),
        )

        await run_activity(
            activity=VMPodScrapperDeletionActivity,
            arg=VMPodScrapperDeletionActivityModel(
                namespace=tenant,
                name="jeeves-worker-metrics",
            ),
            start_to_close_timeout=timedelta(seconds=120),
        )

        # delete deployment
        await run_activity(
            activity=DeploymentDeletionActivity,
            arg=DeploymentDeletionActivityModel(
                namespace=tenant,
                name="jeeves",
            ),
            start_to_close_timeout=timedelta(seconds=120),
        )

        await run_activity(
            activity=DeploymentDeletionActivity,
            arg=DeploymentDeletionActivityModel(
                namespace=tenant,
                name="jeeves-worker",
            ),
            start_to_close_timeout=timedelta(seconds=120),
        )

        # delete config map
        for config_map in ["jeeves-tenant-config", "jeeves-rclone-config"]:
            await run_activity(
                activity=DeleteK8sConfigMapActivity,
                arg=DeleteK8sConfigMapActivityModel(
                    namespace=tenant,
                    name=config_map,
                ),
                start_to_close_timeout=timedelta(seconds=120),
            )

        await run_activity(
            activity=RedisDeleteNamespaceActivity,
            arg=RedisDeleteNamespaceActivityModel(
                namespace=f"jeeves_{tenant}",
                product="jeeves",
            ),
            start_to_close_timeout=timedelta(seconds=120),
        )

        await run_activity(
            activity=DeleteTemporalNamespaceActivity,
            arg=DeleteTemporalNamespaceActivityModel(
                namespace=f"jeeves_{tenant}",
            ),
            start_to_close_timeout=timedelta(seconds=120),
        )

        await run_activity(
            activity=VespaDeleteActivity,
            arg=VespaDeleteActivityModel(
                schema_name=f"jeeves_{tenant}",
            ),
            start_to_close_timeout=timedelta(seconds=120),
        )

        # delete database migration job
        await run_activity(
            activity=DeleteDatabaseMigrationJobActivity,
            arg=DeleteDatabaseMigrationJobActivityModel(
                namespace=tenant,
                job_name="jeeves-db-schema-migration-job",
            ),
            start_to_close_timeout=timedelta(seconds=120),
        )

        await run_activity(
            activity=DeleteSupavisorTenantActivity,
            arg=DeleteSupavisorTenantActivityModel(
                supavisor_tenant_name=f"jeeves_{tenant}",
            ),
            start_to_close_timeout=timedelta(seconds=120),
        )

        await run_activity(
            activity=DeletePostgresUserActivity,
            arg=DeletePostgresUserActivityModel(
                username=f"jeeves_{tenant}",
                database_name="jeeves",
            ),
            start_to_close_timeout=timedelta(seconds=120),
        )

        await run_activity(
            activity=DeletePostgresSchemaActivity,
            arg=DeletePostgresSchemaActivityModel(
                schema_name=f"jeeves_{tenant}",
                database_name="jeeves",
            ),
            start_to_close_timeout=timedelta(seconds=120),
        )

        await run_activity(
            activity=DeleteChatwootAccountActivity,
            arg=DeleteChatwootAccountActivityModel(
                tenant=tenant,
                product="jeeves",
                vault="Jeeves",
            ),
            start_to_close_timeout=timedelta(seconds=120),
        )

        await run_activity(
            activity=DeleteKeycloakClientActivity,
            arg=DeleteKeycloakClientActivityModel(
                client_name="jeeves",
                realm_name=tenant,
            ),
            start_to_close_timeout=timedelta(seconds=120),
        )

        await run_activity(
            activity=DeleteKeycloakRealmActivity,
            arg=DeleteKeycloakRealmActivityModel(
                client_name="jeeves",
                realm_name=tenant,
            ),
            start_to_close_timeout=timedelta(seconds=120),
        )

        await run_activity(
            activity=DeleteIdpFromHelpinstanceActivity,
            arg=DeleteIdpFromHelpinstanceActivityModel(
                tenant=tenant,
                is_prod=True,
            ),
            start_to_close_timeout=timedelta(seconds=120),
        )

        # delete bucket
        bucket_name = f"{tenant}-{jeeves_config.domain_name.replace('.', '-')}"
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
                domain_name=f"{tenant}.api.{jeeves_config.domain_name}",
                zone_id=jeeves_config.zone_id,
            ),
        )

        # update tenant status
        await run_activity(
            activity=UpdateTenantStatusActivity,
            arg=TenantCliStatus(
                tenant_name=tenant,
                status=TenantStatusEnum.DeProvisioned,
                product=ProductEnum.jeeves,
            ),
            start_to_close_timeout=timedelta(seconds=120),
        )

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
