import dataclasses
from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity
from app.cli.dexit.dexit import DexitSpec


class PostgresSetupActivity(Activity):
    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="PostgresSetupActivity")
    async def defn(dexit: DexitSpec):
        """
        Callable for the activity
        """
        from app.cli.dexit.postgresSetup import setup_postgres
        await setup_postgres(
            dexit=dexit
        )


class NamespaceSetupActivity(Activity):
    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="namespace_setup_activity")
    async def defn(dexit: DexitSpec):
        """
        Callable for the activity
        """
        # create namespace in k8s
        from app.cli.dexit.namespaceSetup import Namespace
        Namespace(dexit=dexit).put()


class ConfigmapSetupActivity(Activity):
    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="configmap_setup_activity")
    async def defn(dexit: DexitSpec):
        """
        Callable for the activity
        """
        from app.cli.dexit.configMapSetup import ConfigMapClass
        ConfigMapClass(dexit=dexit, config_map=ConfigMapClass.TENANT_CONFIG).put()
        ConfigMapClass(dexit=dexit, config_map=ConfigMapClass.ENV_CONFIG).put()
        ConfigMapClass(dexit=dexit, config_map=ConfigMapClass.VECTOR_CONFIG).put()


class PVCSetupActivity(Activity):

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="pvc_setup_activity")
    async def defn(dexit: DexitSpec):
        """
        Callable for the activity
        """
        # create PVC in k8s for namespace
        from app.cli.dexit.pvcSetup import PVC
        PVC(dexit=dexit).put()


class SecretSetupActivity(Activity):
    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="secret_setup_activity")
    async def defn(dexit: DexitSpec):
        """
        Callable for the activity
        """
        # create secret in k8s for namespace
        from app.cli.dexit.secretSetup import Secret
        from app.core.settings import get_settings, AppSettings

        config: AppSettings = get_settings()

        # Create registry secret for pulling images
        Secret(
            dexit=dexit,
            name="registrycred",
            type="kubernetes.io/dockerconfigjson",
            data={
                ".dockerconfigjson": config.docker_image_pull_secret
            }
        ).put()


class DnsSetupActivity(Activity):
    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="dns_setup_activity")
    async def defn(dexit: DexitSpec):
        """
        Callable for the activity
        """
        # Create DNS
        from app.cli.dexit.dnsSetup import dns_setup
        await dns_setup(dexit=dexit)


class UiSetupActivity(Activity):
    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="ui_setup_activity")
    async def defn(dexit: DexitSpec):
        """
        Callable for the activity
        """
        # Deploy ui
        from app.cli.dexit.UISetup import UISetup
        UISetup(dexit=dexit).deploy()


class KeycloakRealmSetupActivity(Activity):
    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="keycloak_realm_setup_activity")
    async def defn(dexit: DexitSpec):
        """
        Callable for the activity
        """
        # Deploy keycloak
        from app.cli.dexit.keycloakRealmSetup import create_realm_and_users
        await create_realm_and_users(dexit=dexit)


class NovuSetupActivity(Activity):
    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="novu_setup_activity")
    async def defn(dexit: DexitSpec):
        """
        Callable for the activity
        """
        # Setup novu
        from app.cli.dexit.novuSetup import NovuSetup
        NovuSetup(dexit=dexit).setup_novu()


class ProvisioningJobActivity(Activity):
    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="provisioning_job_activity")
    async def defn(dexit: DexitSpec):
        """
        Callable for the activity
        """
        # Check provisioning status
        from app.cli.dexit.Job import AtlasJob, VespaJob
        atlas_job = AtlasJob(dexit=dexit)
        atlas_job.delete()
        atlas_job.put()

        vespa_job = VespaJob(dexit=dexit)
        vespa_job.delete()
        vespa_job.put()


class KubernetesServiceActivity(Activity):
    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="kubernetes_service_activity")
    async def defn(dexit: DexitSpec):
        """
        Callable for the activity
        """
        # Create k8s service
        from app.cli.dexit.serviceSetup import Service
        Service(dexit=dexit).put()


class KubernetesVirtualServiceActivity(Activity):
    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="kubernetes_virtual_service_activity")
    async def defn(dexit: DexitSpec):
        """
        Callable for the activity
        """
        # Create k8s virtual service
        from app.cli.dexit.istioVitualService import IstioVirtualService
        IstioVirtualService(dexit=dexit).put()


class DeploymentActivity(Activity):
    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="deployment_activity")
    async def defn(dexit: DexitSpec):
        """
        Callable for the activity
        """
        # Deploy k8s deployment
        from app.cli.dexit.depolyment import DeploymentServer, DeploymentCli
        DeploymentServer(dexit=dexit).put()
        DeploymentCli(dexit=dexit).put()


class VmPodScraperActivity(Activity):
    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="vm_pod_scraper_activity")
    async def defn(dexit: DexitSpec):
        """
        Callable for the activity
        """
        # Scrape pod logs
        from app.cli.dexit.vmPodScraper import VMPodScrapperServer
        VMPodScrapperServer(dexit=dexit).put()


class GrafanaAlertsActivity(Activity):
    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="grafana_alerts_activity")
    async def defn(dexit: DexitSpec):
        """
        Callable for the activity
        """
        # Todo: Implement this
        # Setup grafana alerts
        # from app.cli.dexit.grafanaAlerts import create_grafana_alerts
        # await create_grafana_alerts(dexit=dexit)


@dataclasses.dataclass
class TenantStatus:
    """
    TenantStatus dataclass
    """
    tenant_name: str
    status: str
    error_msg: None | str = None


class UpdateTenantStatusActivity(Activity):
    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="UpdateTenantStatusActivity")
    async def defn(activity_input: TenantStatus):
        """
        Callable for the activity
        """
        # Update tenant status
        from app.cli.common.tenantStatus import update_tenant_status
        from app.models.tenant import TenantStatusEnum
        from app.cli.dexit.dexit import ProductName
        await update_tenant_status(
            tenant_name=activity_input.tenant_name,
            product=ProductName,
            status=TenantStatusEnum(activity_input.status),
            error_message=activity_input.error_msg
        )


class TemporalNamespaceCreationActivity(Activity):
    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="temporal_namespace_creation_activity")
    async def defn(dexit: DexitSpec):
        """
        Callable for the activity
        """
        # Create temporal namespace
        from app.cli.dexit.temporalNamespaceCreation import TemporalNamespaceCreation
        await TemporalNamespaceCreation(dexit=dexit).create_temporal_namespace()
