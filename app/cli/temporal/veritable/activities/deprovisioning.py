import dataclasses
from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity, IODataclass
from app.cli.veritable.common import VeritableSpec


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
    async def defn(veritable: VeritableSpec):
        """
        Callable for the activity
        """
        from app.cli.veritable.serviceSetup import Service
        Service(veritable=veritable).delete()


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
    async def defn(activity_input: VeritableSpec):
        """
        Callable for the activity
        """
        from app.cli.veritable.istioVitualService import IstioVirtualService
        IstioVirtualService(activity_input).delete()


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
    async def defn(activity_input: VeritableSpec):
        """
        Callable for the activity
        """
        from app.cli.veritable.provisioningJob import ProvisioningJob
        ProvisioningJob(veritable=activity_input).delete()


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
    async def defn(activity_input: VeritableSpec):
        """
        Callable for the activity
        """
        from app.cli.veritable.depolyment import DeploymentServer, DeploymentCli
        DeploymentServer(veritable=activity_input).delete()
        DeploymentCli(veritable=activity_input).delete()


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
    async def defn(activity_input: VeritableSpec):
        """
        Callable for the activity
        """
        from app.cli.veritable.configMapSetup import ConfigMapClass
        ConfigMapClass(veritable=activity_input, config_map=ConfigMapClass.TENANT_CONFIG).delete()
        ConfigMapClass(veritable=activity_input, config_map=ConfigMapClass.PROVISION_CONFIG).delete()
        ConfigMapClass(veritable=activity_input, config_map=ConfigMapClass.ENV_CONFIG).delete()
        ConfigMapClass(veritable=activity_input, config_map=ConfigMapClass.VECTOR_CONFIG).delete()


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
    async def defn(activity_input: VeritableSpec):
        """
        Callable for the activity
        """
        from app.cli.veritable.pvcSetup import PVC
        PVC(veritable=activity_input).delete()


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
    async def defn(activity_input: VeritableSpec):
        """
        Callable for the activity
        """
        from app.cli.veritable.UISetup import UISetup
        UISetup(veritable=activity_input).delete()


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
    async def defn(activity_input: VeritableSpec):
        """
        Callable for the activity
        """
        from app.cli.veritable.dnsSetup import dns_teardown
        await dns_teardown(tenant_name=activity_input.tenant)


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
    async def defn(activity_input: VeritableSpec):
        """
        Callable for the activity
        """
        from app.cli.veritable.vmPodScraper import VMPodScrapperServer, VMPodScrapperCli
        VMPodScrapperServer(veritable=activity_input).delete()
        VMPodScrapperCli(veritable=activity_input).delete()
