import dataclasses
from datetime import timedelta
from temporalio.common import RetryPolicy
from app.cli.penknife.models.penknifespec import PenknifeSpec
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from temporalio import activity


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
            maximum_attempts=5,
        )
    
    @staticmethod
    @activity.defn(name="PostgresSetupActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.penknife.postgresSetup import setup_postgres

        await setup_postgres(penknife=penknife)

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
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="NamespaceSetupActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        # create namespace in k8s
        from app.cli.penknife.namespaceSetup import Namespace

        Namespace(penknife=penknife).put()

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
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="ConfigmapSetupActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.penknife.configMapSetup import ConfigMapClass

        ConfigMapClass(penknife=penknife, config_map=ConfigMapClass.TENANT_CONFIG).put()
        ConfigMapClass(penknife=penknife, config_map=ConfigMapClass.RCLONE_CONFIG).put()
        ConfigMapClass(penknife=penknife, config_map=ConfigMapClass.VECTOR_CONFIG).put()
        ConfigMapClass(penknife=penknife, config_map=ConfigMapClass.STATE_STORE_CONFIG).put()

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
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="PVCSetupActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        # create PVC in k8s for namespace
        from app.cli.penknife.pvcSetup import PVC

        PVC(penknife=penknife).put()

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
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="SecretSetupActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        # create secret in k8s for namespace
        from app.cli.penknife.secretSetup import Secret
        from app.core.settings import get_settings, AppSettings

        config: AppSettings = get_settings()

        # Create registry secret for pulling images
        Secret(
            penknife=penknife,
            name="registrycred",
            type="kubernetes.io/dockerconfigjson",
            data={".dockerconfigjson": config.docker_image_pull_secret},
        ).put()

        # Create redis secret for redis password
        Secret(
            penknife=penknife,
            name="cache-secret",
            data={"REDIS_PASSWORD": config.cache_admin_password},
        ).put()

class StateFullSetSetupActivity(Activity):
    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="StateFullSetSetupActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        # create stateful set in k8s
        from app.cli.penknife.statefulSetup import StateFullSet

        await StateFullSet(penknife=penknife).put()

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
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="DnsSetupActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        # Create DNS
        from app.cli.penknife.dnsSetup import dns_setup

        await dns_setup(penknife=penknife)

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
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="UiSetupActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        # Deploy ui
        from app.cli.penknife.UISetup import UISetup

        UISetup(penknife=penknife).deploy()

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
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="KeycloakRealmSetupActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        # Deploy keycloak
        from app.cli.penknife.keycloakRealmSetup import create_realm_and_users
        await create_realm_and_users(penknife=penknife)

# TODO: MISSING

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
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="NovuSetupActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        # Setup novu
        from app.cli.penknife.novuSetup import NovuSetup

        NovuSetup(penknife=penknife).setup_novu()


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
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="ProvisioningJobActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        # Check provisioning status
        from app.cli.penknife.Job import DatabaseSchemaMigrationJob

        atlas_job = DatabaseSchemaMigrationJob(penknife=penknife)
        atlas_job.delete()
        atlas_job.put()

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
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="KubernetesServiceActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        # Create k8s service
        from app.cli.penknife.serviceSetup import Service

        Service(penknife=penknife).put()

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
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="KubernetesVirtualServiceActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        # Create k8s virtual service
        from app.cli.penknife.istioVirtualService import IstioVirtualService

        IstioVirtualService(penknife=penknife).put()

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
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="DeploymentActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        # Deploy k8s deployment
        from app.cli.penknife.deployment import DeploymentServer, DeploymentCli

        DeploymentServer(penknife=penknife).put()
        DeploymentCli(penknife=penknife).put()

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
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="VmPodScraperActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        # Scrape pod logs
        from app.cli.penknife.vmPodScrapper import VMPodScrapperServer

        VMPodScrapperServer(penknife=penknife).put()

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
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="UpdateTenantStatusActivity")
    async def defn(activity_input: TenantStatus) -> None:
        """
        Callable for the activity
        """
        # Update tenant status
        from app.cli.common.tenantStatus import update_tenant_status
        from app.cli.penknife.penknife import ProductName
        from app.models.tenant import TenantStatusEnum

        status = TenantStatusEnum(activity_input.status)

        await update_tenant_status(
            tenant_name=activity_input.tenant_name,
            product=ProductName,
            status=status,
            error_message=activity_input.error_msg,
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
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="TemporalNamespaceCreationActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        # Create temporal namespace
        from app.cli.penknife.temporalNamespaceCreation import TemporalNamespaceCreation

        await TemporalNamespaceCreation(penknife=penknife).create_temporal_namespace()

class SendMailActivity(Activity):
    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="SendMailActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        # Send mail to customer
        from app.cli.penknife.mail import onboard_success

        onboard_success(penknife=penknife)
