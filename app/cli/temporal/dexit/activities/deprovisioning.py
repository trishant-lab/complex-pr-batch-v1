from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.dexit.models.dexitSpec import DexitSpec
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
    async def defn(dexit: DexitSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.dexit.serviceSetup import Service

        Service(dexit=dexit).delete()


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
    async def defn(dexit: DexitSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.dexit.istioVitualService import IstioVirtualService

        IstioVirtualService(dexit).delete()


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
    async def defn(dexit: DexitSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.dexit.Job import AtlasJob

        AtlasJob(dexit=dexit).delete()


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
    async def defn(dexit: DexitSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.dexit.depolyment import DeploymentServer, DeploymentCli

        DeploymentServer(dexit=dexit).delete()
        DeploymentCli(dexit=dexit).delete()


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
    async def defn(dexit: DexitSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.dexit.configMapSetup import ConfigMapClass

        ConfigMapClass(dexit=dexit, config_map=ConfigMapClass.TENANT_CONFIG).delete()
        ConfigMapClass(dexit=dexit, config_map=ConfigMapClass.ENV_CONFIG).delete()
        ConfigMapClass(dexit=dexit, config_map=ConfigMapClass.VECTOR_CONFIG).delete()


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
    async def defn(dexit: DexitSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.dexit.UISetup import UISetup

        UISetup(dexit=dexit).delete()


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
    async def defn(dexit: DexitSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.dexit.dnsSetup import dns_teardown

        await dns_teardown(tenant_name=dexit.tenant)


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
    async def defn(dexit: DexitSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.dexit.vmPodScraper import VMPodScrapperServer

        VMPodScrapperServer(dexit=dexit).delete()
