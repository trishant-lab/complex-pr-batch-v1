from datetime import timedelta
from temporalio.common import RetryPolicy
from temporalio import activity

from app.cli.penknife.models.penknifespec import PenknifeSpec
from app.cli.temporal.core.base import Activity
from app.cli.penknife.penknife import ProductName


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
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.activities.serviceSetup import Service

        Service(tenant=penknife.tenant, product=ProductName).delete()


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
        from app.cli.activities.istioVirtualService import IstioVirtualService
        from app.core.settings import get_settings, AppSettings

        config: AppSettings = get_settings()

        IstioVirtualService(
            tenant=penknife.tenant, domain_name=config.penknife.domain_name, product=ProductName
        ).delete()

        IstioVirtualService(
            tenant=penknife.tenant,
            domain_name=config.penknife.domain_name,
            product=ProductName,
            service_name=f"{ProductName.lower()}-careers-vs",
            host=f"{penknife.tenant}-careers.{config.penknife.domain_name}",
        ).delete()


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
        from app.cli.penknife.Job import DatabaseSchemaMigrationJob

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
        from app.cli.activities.configMapSetup import ConfigMapClass

        tenant_config: dict[str, str] = {"name": "penknife-tenant-config", "key": "tenant-config.json"}
        vector_config: dict[str, str] = {"name": "penknife-cli-vector-config", "key": "vector-config.toml"}
        state_store_config: dict[str, str] = {"name": "penknife-statestore-config", "key": "statestore.yaml"}

        bucket_name = "penknife-config"

        ConfigMapClass(tenant=penknife.tenant, config_map=tenant_config, bucket_name=bucket_name).delete()
        ConfigMapClass(tenant=penknife.tenant, config_map=vector_config, bucket_name=bucket_name).delete()
        ConfigMapClass(tenant=penknife.tenant, config_map=state_store_config, bucket_name=bucket_name).delete()


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
        from app.cli.activities.UISetup import UISetup
        from app.core.settings import get_settings

        UISetup(
            tenant=penknife.tenant,
            domain_name=get_settings().penknife.domain_name,
            repo_name="penknife-ui",
            product_name=ProductName,
        ).delete()

        # TODO: Delete career portal


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
        from app.cli.activities.dnsSetup import dns_teardown
        from app.core.settings import get_settings, AppSettings

        config: AppSettings = get_settings()

        # DNS setup for penknife
        fqdn = f"{penknife.tenant}.{config.penknife.domain_name}."

        await dns_teardown(google_dns_cname=config.google_dns_cname, fqdn=fqdn, zone_name=config.penknife.zone_name)

        # DNS setup for penknife career portal
        career_fqdn = f"{penknife.tenant}-careers.{config.penknife.domain_name}."

        await dns_teardown(
            google_dns_cname=config.google_dns_cname, fqdn=career_fqdn, zone_name=config.penknife.zone_name
        )


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
        from app.cli.activities.vmPodScraper import VMPodScrapperServer

        name = "penknife-metrics"

        VMPodScrapperServer(tenant=penknife.tenant, product=ProductName, name=name).delete()


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
        from app.cli.activities.redisSetup import RedisSetup

        await RedisSetup(tenant=penknife.tenant, product=ProductName, vault_name="Penknife").delete()


# class DeleteStatefulSetActivity(Activity):
#     @staticmethod
#     def get_retry_policy() -> RetryPolicy:
#         """
#         RetryPolicy for the activity
#         """
#         return RetryPolicy(
#             initial_interval=timedelta(seconds=1),
#             backoff_coefficient=2,
#             maximum_interval=timedelta(seconds=10),
#             maximum_attempts=1,
#         )

#     @staticmethod
#     @activity.defn(name="DeleteStatefulSetActivity")
#     async def defn(penknife: PenknifeSpec) -> None:
#         """
#         Callable for the activity
#         """
#         from app.cli.penknife.statefulSetup import StateFullSet

#         StateFullSet(penknife=penknife).delete()


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
        from app.cli.activities.penknifeKeycloakSetup import delete_clients_and_realms

        await delete_clients_and_realms(penknife=penknife)
