from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.jeeves.common import JeevesSpec
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
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        from app.cli.jeeves.serviceSetup import Service
        Service(jeeves=jeeves).delete()


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
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        from app.cli.jeeves.istioVitualService import IstioVirtualService
        IstioVirtualService(jeeves).delete()


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
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        from app.cli.jeeves.Job import AlembicJob, VespaJob
        AlembicJob(jeeves=jeeves).delete()
        VespaJob(jeeves=jeeves).delete()


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
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        from app.cli.jeeves.depolyment import DeploymentServer, DeploymentCli
        DeploymentServer(jeeves=jeeves).delete()
        DeploymentCli(jeeves=jeeves).delete()


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
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        from app.cli.jeeves.configMapSetup import ConfigMapClass
        ConfigMapClass(jeeves=jeeves, config_map=ConfigMapClass.TENANT_CONFIG).delete()
        ConfigMapClass(jeeves=jeeves, config_map=ConfigMapClass.RCLONE_CONFIG).delete()
        ConfigMapClass(jeeves=jeeves, config_map=ConfigMapClass.STATE_STORE_CONFIG).delete()
        ConfigMapClass(jeeves=jeeves, config_map=ConfigMapClass.VECTOR_CONFIG).delete()


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
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        from app.cli.jeeves.pvcSetup import PVC
        PVC(jeeves=jeeves).delete()


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
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        from app.cli.jeeves.UISetup import UISetup
        UISetup(jeeves=jeeves).delete()


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
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        from app.cli.jeeves.dnsSetup import dns_teardown
        await dns_teardown(tenant_name=jeeves.tenant)


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
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        from app.cli.jeeves.vmPodScraper import VMPodScrapperServer
        VMPodScrapperServer(jeeves=jeeves).delete()


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
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        from app.cli.jeeves.statefulSetup import StateFullSet
        StateFullSet(jeeves=jeeves).delete()