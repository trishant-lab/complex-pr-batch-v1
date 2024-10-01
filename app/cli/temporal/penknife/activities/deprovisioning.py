
from datetime import timedelta
from temporalio.common import RetryPolicy
from temporalio import activity

from app.cli.penknife.models.penknifespec import PenknifeSpec
from app.cli.temporal.core.base import Activity


class DeleteKubernetesServiceActivity(Activity):
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
    @activity.defn(name="DeleteKubernetesServiceActivity")
    async def defn(penkife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.penknife.serviceSetup import Service

        Service(penknife=penkife).delete()

class DeleteKubernetesVirtualServiceActivity(Activity):
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
    @activity.defn(name="DeleteKubernetesVirtualServiceActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.penknife.istioVirtualService import IstioVirtualService

        IstioVirtualService(penknife=penknife).delete()

class DeleteProvisioningJobActivity(Activity):
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
    @activity.defn(name="DeleteProvisioningJobActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.penknife.Job import DatabaseSchemaMigrationJob, VespaJob

        DatabaseSchemaMigrationJob(penknife=penknife).delete()

class DeleteDeploymentActivity(Activity):
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
    @activity.defn(name="DeleteDeploymentActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.penknife.deployment import DeploymentServer, DeploymentCli

        DeploymentServer(penknife=penknife).delete()
        DeploymentCli(penknife=penknife).delete()

class DeleteConfigMapActivity(Activity):
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
    @activity.defn(name="DeleteConfigMapActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.penknife.configMapSetup import ConfigMapClass

        ConfigMapClass(penknife=penknife, config_map=ConfigMapClass.TENANT_CONFIG).delete()
        ConfigMapClass(penknife=penknife, config_map=ConfigMapClass.STATE_STORE_CONFIG).delete()
        ConfigMapClass(penknife=penknife, config_map=ConfigMapClass.VECTOR_CONFIG).delete()

class DeletePVCActivity(Activity):
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
    @activity.defn(name="DeletePVCActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.penknife.pvcSetup import PVC

        PVC(penknife=penknife).delete()

class DropUIBundlesActivity(Activity):
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
    @activity.defn(name="DropUIBundlesActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.penknife.UISetup import UISetup

        UISetup(penknife=penknife).delete()

class DeleteDNSActivity(Activity):
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
    @activity.defn(name="DeleteDNSActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.penknife.dnsSetup import dns_teardown

        await dns_teardown(tenant_name=penknife.tenant)


class DeleteVMScraperActivity(Activity):
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
    @activity.defn(name="DeleteVMScraperActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.penknife.vmPodScrapper import VMPodScrapperServer

        VMPodScrapperServer(penknife=penknife).delete()

class DeleteRedisNamespace(Activity):
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
    @activity.defn(name="DeleteRedisNamespace")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.penknife.statefulSetup import StateFullSet

        StateFullSet(penknife=penknife).delete()

class DeleteStatefulSetActivity(Activity):
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
    @activity.defn(name="DeleteStatefulSetActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.penknife.statefulSetup import StateFullSet

        StateFullSet(penknife=penknife).delete()

class DeleteKeycloakRealmActivity(Activity):
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
    @activity.defn(name="DeleteKeycloakRealmActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.penknife.keycloakRealmSetup import delete_clients_and_realms

        await delete_clients_and_realms(penknife=penknife)
