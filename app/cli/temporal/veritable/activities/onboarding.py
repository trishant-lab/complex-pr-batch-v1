import dataclasses
from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity
from app.cli.veritable.common import VeritableSpec


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
    @activity.defn(name="postgres_setup_activity")
    async def defn(veritable: VeritableSpec):
        """
        Callable for the activity
        """
        from app.cli.veritable.postgresSetup import execute_postgres_setup_workflow
        await execute_postgres_setup_workflow(
            veritable=veritable
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
    async def defn(veritable: VeritableSpec):
        """
        Callable for the activity
        """
        # create namespace in k8s
        from app.cli.veritable.k8sSetup import create_namespace
        await create_namespace(veritable=veritable)


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
    async def defn(veritable: VeritableSpec):
        """
        Callable for the activity
        """
        from app.cli.veritable.configMapSetup import create_configmap
        # create configmap in k8s for namespace
        await create_configmap(veritable=veritable)


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
    async def defn(veritable: VeritableSpec):
        """
        Callable for the activity
        """
        # create PVC in k8s for namespace
        from app.cli.veritable.k8sSetup import create_pvc
        await create_pvc(veritable=veritable)


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
    async def defn(veritable: VeritableSpec):
        """
        Callable for the activity
        """
        # create secret in k8s for namespace
        from app.cli.veritable.k8sSetup import create_secret_service
        await create_secret_service(veritable=veritable)


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
    async def defn(veritable: VeritableSpec):
        """
        Callable for the activity
        """
        # Create DNS
        from app.cli.veritable.dnsSetup import dns_setup
        await dns_setup(veritable=veritable)


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
    async def defn(veritable: VeritableSpec):
        """
        Callable for the activity
        """
        # Deploy ui
        from app.cli.veritable.deployUi import deploy_ui_func
        await deploy_ui_func(veritable=veritable)


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
    async def defn(veritable: VeritableSpec):
        """
        Callable for the activity
        """
        # Deploy keycloak
        from app.cli.veritable.keycloakRealmSetup import create_realm_and_users
        await create_realm_and_users(veritable=veritable)


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
    async def defn(veritable: VeritableSpec):
        """
        Callable for the activity
        """
        # Check provisioning status
        from app.cli.veritable.provisioningJob import provisioning_job
        await provisioning_job(veritable=veritable)


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
    async def defn(veritable: VeritableSpec):
        """
        Callable for the activity
        """
        # Create k8s service
        from app.cli.veritable.k8sSetup import create_k8s_service
        await create_k8s_service(veritable=veritable)


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
    async def defn(veritable: VeritableSpec):
        """
        Callable for the activity
        """
        # Create k8s virtual service
        from app.cli.veritable.istioVitualService import create_istio_virtual_service
        await create_istio_virtual_service(veritable=veritable)


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
    async def defn(veritable: VeritableSpec):
        """
        Callable for the activity
        """
        # Deploy k8s deployment
        from app.cli.veritable.depolyment import deploy_server_and_cli
        await deploy_server_and_cli(veritable=veritable)


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
    async def defn(veritable: VeritableSpec):
        """
        Callable for the activity
        """
        # Scrape pod logs
        from app.cli.veritable.vmPodScraper import vm_pod_scraper
        await vm_pod_scraper(veritable=veritable)


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
    async def defn(veritable: VeritableSpec):
        """
        Callable for the activity
        """
        # Setup grafana alerts
        from app.cli.veritable.grafanaAlerts import create_grafana_alerts
        await create_grafana_alerts(veritable)


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
    @activity.defn(name="update_tenant_status_activity")
    async def defn(activity_input: TenantStatus):
        """
        Callable for the activity
        """
        # Update tenant status
        from app.cli.veritable.tenantStatus import update_tenant_status
        await update_tenant_status(
            tenant_name=activity_input.tenant_name, status=activity_input.status, error_message=activity_input.error_msg
        )
