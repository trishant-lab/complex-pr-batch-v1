from collections.abc import Callable
from datetime import timedelta

import pydash
from temporalio import workflow

from app.cli.temporal.activities.chatwootSetup import DeleteChatwootAccountActivity, DeleteChatwootAccountActivityModel
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
from app.cli.temporal.activities.deployment import DeploymentDeletionActivity, DeploymentDeletionActivityModel
from app.cli.temporal.activities.k8sIstioVirtualService import (
    DeleteKubernetesIstioVirtualServiceActivity,
    DeleteKubernetesIstioVirtualServiceActivityModel,
)
from app.cli.temporal.activities.k8sService import DeleteKubernetesServiceActivity, DeleteKubernetesServiceActivityModel
from app.cli.temporal.activities.k8sconfigMap import DeleteK8sConfigMapActivity, DeleteK8sConfigMapActivityModel
from app.cli.temporal.activities.keycloakSetup import (
    DeleteIdpFromHelpinstanceActivity,
    DeleteIdpFromHelpinstanceActivityModel,
    DeleteKeycloakClientActivity,
    DeleteKeycloakClientActivityModel,
    DeleteKeycloakRealmActivity,
    DeleteKeycloakRealmActivityModel,
)
from app.cli.temporal.activities.postgresSetup import (
    DeletePostgresSchemaActivity,
    DeletePostgresSchemaActivityModel,
    DeletePostgresUserActivity,
    DeletePostgresUserActivityModel,
    DeleteSupavisorTenantActivity,
    DeleteSupavisorTenantActivityModel,
)
from app.cli.temporal.activities.redis import RedisDeleteNamespaceActivity, RedisDeleteNamespaceActivityModel
from app.cli.temporal.activities.temporalNamespace import (
    DeleteTemporalNamespaceActivity,
    DeleteTemporalNamespaceActivityModel,
)
from app.cli.temporal.activities.updateTenantStatus import TenantStatus, UpdateTenantStatusActivity
from app.cli.temporal.activities.vespaJob import VespaDeleteActivity, VespaDeleteActivityModel
from app.cli.temporal.activities.vmPodScrapper import VMPodScrapperDeletionActivity, VMPodScrapperDeletionActivityModel
from app.cli.temporal.core.base import Workflow

from app.cli.temporal.jeeves.jeeves import JeevesSpec


from app.core.settings import get_settings, JeevesSettings


@workflow.defn(name="JeevesDeProvisioningWorkflow")
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

        await workflow.execute_activity(
            VMPodScrapperDeletionActivity.defn,
            arg=VMPodScrapperDeletionActivityModel(
                namespace=tenant,
                name="jeeves-worker-metrics",
            ),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=VMPodScrapperDeletionActivity.get_retry_policy(),
        )

        # delete deployment
        await workflow.execute_activity(
            DeploymentDeletionActivity.defn,
            arg=DeploymentDeletionActivityModel(
                namespace=tenant,
                name="jeeves",
            ),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=DeploymentDeletionActivity.get_retry_policy(),
        )

        await workflow.execute_activity(
            DeploymentDeletionActivity.defn,
            arg=DeploymentDeletionActivityModel(
                namespace=tenant,
                name="jeeves-worker",
            ),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=DeploymentDeletionActivity.get_retry_policy(),
        )

        # delete config map
        for config_map in ["jeeves-tenant-config", "jeeves-rclone-config"]:
            await workflow.execute_activity(
                DeleteK8sConfigMapActivity.defn,
                arg=DeleteK8sConfigMapActivityModel(
                    namespace=tenant,
                    name=config_map,
                ),
                start_to_close_timeout=timedelta(seconds=120),
                retry_policy=DeleteK8sConfigMapActivity.get_retry_policy(),
            )

        await workflow.execute_activity(
            RedisDeleteNamespaceActivity.defn,
            arg=RedisDeleteNamespaceActivityModel(
                namespace=f"jeeves_{tenant}",
                product="jeeves",
            ),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=RedisDeleteNamespaceActivity.get_retry_policy(),
        )

        await workflow.execute_activity(
            DeleteTemporalNamespaceActivity.defn,
            arg=DeleteTemporalNamespaceActivityModel(
                namespace=f"jeeves_{tenant}",
            ),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=DeleteTemporalNamespaceActivity.get_retry_policy(),
        )

        await workflow.execute_activity(
            VespaDeleteActivity.defn,
            arg=VespaDeleteActivityModel(
                schema_name=f"jeeves_{tenant}",
            ),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=VespaDeleteActivity.get_retry_policy(),
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

        await workflow.execute_activity(
            DeleteSupavisorTenantActivity.defn,
            arg=DeleteSupavisorTenantActivityModel(
                supavisor_tenant_name=f"jeeves_{tenant}",
            ),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=DeleteSupavisorTenantActivity.get_retry_policy(),
        )

        await workflow.execute_activity(
            DeletePostgresUserActivity.defn,
            arg=DeletePostgresUserActivityModel(
                username=f"jeeves_{tenant}",
                database_name="jeeves",
            ),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=DeletePostgresUserActivity.get_retry_policy(),
        )

        await workflow.execute_activity(
            DeletePostgresSchemaActivity.defn,
            arg=DeletePostgresSchemaActivityModel(
                schema_name=f"jeeves_{tenant}",
                database_name="jeeves",
            ),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=DeletePostgresSchemaActivity.get_retry_policy(),
        )

        await workflow.execute_activity(
            DeleteChatwootAccountActivity.defn,
            arg=DeleteChatwootAccountActivityModel(
                tenant=tenant,
                product="jeeves",
                vault="Jeeves",
            ),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=DeleteChatwootAccountActivity.get_retry_policy(),
        )

        await workflow.execute_activity(
            DeleteKeycloakClientActivity.defn,
            arg=DeleteKeycloakClientActivityModel(
                client_name="jeeves",
                realm_name=tenant,
            ),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=DeleteKeycloakClientActivity.get_retry_policy(),
        )

        await workflow.execute_activity(
            DeleteKeycloakRealmActivity.defn,
            arg=DeleteKeycloakRealmActivityModel(
                client_name="jeeves",
                realm_name=tenant,
            ),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=DeleteKeycloakRealmActivity.get_retry_policy(),
        )

        await workflow.execute_activity(
            DeleteIdpFromHelpinstanceActivity.defn,
            arg=DeleteIdpFromHelpinstanceActivityModel(
                tenant=tenant,
                is_prod=True,
            ),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=DeleteIdpFromHelpinstanceActivity.get_retry_policy(),
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
                tenant_name=tenant,
                status="DeProvisioned",
            ),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
        )
