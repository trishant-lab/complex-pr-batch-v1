import dataclasses
from datetime import timedelta
from uuid import uuid4
from temporalio.common import RetryPolicy
from app.cli.temporal.penknife.models.penknifespec import PenknifeSpec, TenantType
from app.cli.temporal.core.base import Activity
from temporalio import activity
from app.cli.temporal.penknife.penknife import ProductName


# ProductName = "penknife"
OnePasswordVault = "Penknife"


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
        from app.cli.activities.postgresSchemaSetup import setup_postgres
        from app.cli.temporal.penknife import TemplatePath
        from app.core.settings import get_settings

        database_name = "penknife"
        schema_name = penknife.tenant
        vault_name = "Penknife"

        await setup_postgres(
            tenant=penknife.tenant,
            product_name=ProductName,
            schema_name=schema_name,
            database_name=database_name,
            vault_name=vault_name,
            template_path=TemplatePath,
            config=get_settings().penknife,
            keycloak_db=True,
            matomo_db=False,
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
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="NamespaceSetupActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        # create namespace in k8s
        from app.cli.activities.namespaceSetup import Namespace

        Namespace(tenant=penknife.tenant).put()


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
        from app.cli.activities.configMapSetup import ConfigMapClass

        tenant_config: dict[str, str] = {"name": "penknife-tenant-config", "key": "tenant-config.json"}
        vector_config: dict[str, str] = {"name": "penknife-cli-vector-config", "key": "vector-config.toml"}
        state_store_config: dict[str, str] = {"name": "penknife-statestore-config", "key": "statestore.yaml"}

        bucket_name = "penknife-config"

        ConfigMapClass(
            tenant=penknife.tenant,
            config_map=tenant_config,
            bucket_name=bucket_name,
            tenant_type=TenantType.get_tenant_type(penknife.tenantType),
        ).put()
        ConfigMapClass(tenant=penknife.tenant, config_map=vector_config, bucket_name=bucket_name).put()
        ConfigMapClass(tenant=penknife.tenant, config_map=state_store_config, bucket_name=bucket_name).put()


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
        from app.cli.activities.secretSetup import Secret
        from app.core.settings import get_settings, AppSettings

        config: AppSettings = get_settings()

        # Create registry secret for pulling images
        Secret(
            tenant=penknife.tenant,
            name="registrycred",
            type="kubernetes.io/dockerconfigjson",
            data={".dockerconfigjson": config.docker_image_pull_secret},
        ).put()

        # Create redis secret for redis password
        Secret(
            tenant=penknife.tenant,
            name="cache-secret",
            data={"REDIS_PASSWORD": config.cache_admin_password},
        ).put()


class RedisSetupActivity(Activity):
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
    @activity.defn(name="RedisSetupActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        # create redisSetup set in k8s
        from app.cli.activities.redisSetup import RedisSetup

        await RedisSetup(tenant=penknife.tenant, product=ProductName, vault_name="Penknife").put()


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
        from app.cli.activities.dnsSetup import dns_setup
        from app.core.settings import get_settings, AppSettings

        config: AppSettings = get_settings()

        # DNS setup for penknife
        fqdn = f"{penknife.tenant}.{config.penknife.domain_name}."

        await dns_setup(google_dns_cname=config.google_dns_cname, fqdn=fqdn, zone_name=config.penknife.zone_name)

        # DNS setup for penknife career portal
        career_fqdn = f"{penknife.tenant}-careers.{config.penknife.domain_name}."

        await dns_setup(google_dns_cname=config.google_dns_cname, fqdn=career_fqdn, zone_name=config.penknife.zone_name)


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
        from app.cli.activities.UISetup import UISetup
        from app.core.settings import get_settings, AppSettings

        config: AppSettings = get_settings()

        environment: str = config.env
        image_tag = "production" if environment == "production" else "sprint"

        if environment == "production":
            dest_dir = f"{penknife.tenant}.{config.penknife.domain_name}/"
        else:
            dest_dir = f"{penknife.tenant}.{config.penknife.domain_name}/{image_tag}"

        repo_name = "penknife-ui"

        src_object_name = f"{repo_name}/{image_tag}/bundle.zip"

        # Deploy UI for penknife
        UISetup(
            src_object_name=src_object_name,
            dest_dir=dest_dir,
            product_name=ProductName,
        ).deploy()

        # Deploy UI for penknife career portal
        dest_dir = f"{penknife.tenant}-careers.{config.penknife.domain_name}/"

        UISetup(
            src_object_name="artifacts/penknife-careers/bundle.zip",
            dest_dir=dest_dir,
            product_name=ProductName,
        ).deploy()


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
        from app.cli.activities.penknifeKeycloakSetup import create_realm_and_users

        await create_realm_and_users(penknife=penknife)


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
        from app.cli.activities.jeevesNovuSetup import NovuSetup

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
        from kubernetes.client.models import V1VolumeMount, V1Volume, V1EnvVar, V1ConfigMapVolumeSource, V1KeyToPath
        from app.cli.activities.databaseMigrationJob import DatabaseMigrationJob
        from app.onepasswordutil import OnePasswordUtil
        from app.core.settings import get_settings

        postgres_user = f"penknife_{penknife.tenant}"
        postgres_password = OnePasswordUtil(
            tenant=f"Penknife_{penknife.tenant}",
            server_item="application-config",
            vault=OnePasswordVault,
        ).get_key("pg_password")
        image_tag = "production" if get_settings().env == "production" else "sprint"
        docker_image = f"registry.314ecorp.tech/penknife-app:{image_tag}"

        volume_mount = V1VolumeMount(
            name="penknife-tenant-config",
            mount_path="/config/tenant-config.json",
            sub_path="tenant-config.json",
            read_only=True,
        )

        volume = V1Volume(
            name="penknife-tenant-config",
            config_map=V1ConfigMapVolumeSource(
                name="penknife-tenant-config",
                items=[V1KeyToPath(key="tenant-config.json", path="tenant-config.json")],
            ),
        )

        envs = [
            V1EnvVar(name="POSTGRES_PASSWORD", value=postgres_password),
            V1EnvVar(name="POSTGRES_USER", value=postgres_user),
            V1EnvVar(name="APP_CONFIG_FILE", value="/config/tenant-config.json"),
            V1EnvVar(name="DEPLOYMENT", value=get_settings().env),
            V1EnvVar(name="CLIENT_CODE", value=penknife.tenant),
        ]

        database_migration_job = DatabaseMigrationJob(
            tenant=penknife.tenant,
            product=ProductName,
            job_name="penknife-db-schema-migration-job",
            postgres_user=postgres_user,
            postgres_password=postgres_password,
            docker_image=docker_image,
            volume_mounts=[volume_mount],
            volumes=[volume],
            container_envs=envs,
            script_path="/app/atlas/atlas_script.py",
        )
        database_migration_job.delete()
        database_migration_job.put()


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
        from app.cli.activities.serviceSetup import Service

        Service(tenant=penknife.tenant, product=ProductName, port=8000).put()


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
        # from app.cli.penknife.istioVirtualService import IstioVirtualService, IstioCareersVirtualService
        from app.cli.activities.istioVirtualService import IstioVirtualService
        from app.core.settings import get_settings, AppSettings

        config: AppSettings = get_settings()
        env = config.env
        image_tag = "sprint" if env == "integration" else "production"

        # penknife istio config
        http_list = []
        # http_api router
        http_api = {
            "name": "penknife-api",
            "route": [
                {
                    "destination": {
                        "host": f"penknife.{penknife.tenant}.svc.cluster.local",
                        "port": {"number": 8000},
                    },
                    "headers": {
                        "response": {"add": {"Strict-Transport-Security": "max-age=31536000;includeSubDomains;preload"}}
                    },
                }
            ],
            "match": [
                {"uri": {"regex": "^/public/api/v1/.*"}},
                {"uri": {"regex": "^/api/v1/.*"}},
                {"uri": {"prefix": "/docs"}},
                {"uri": {"prefix": "/redoc"}},
            ],
        }
        http_list.append(http_api)
        # http_redirect router
        if env != "production":
            http_redirect = {
                "name": "redirect",
                "match": [
                    {
                        "uri": {"exact": "/"},
                    }
                ],
                "redirect": {"uri": f"/{image_tag}/"},
            }
            http_list.append(http_redirect)
        # http_ui router
        http_ui = {
            "name": "penknife-ui",
            "route": [
                {
                    "destination": {
                        "host": "varnish-svc.varnish.svc.cluster.local",
                        "port": {"number": 80},
                    },
                    "headers": {"response": {"remove": ["x-envoy-upstream-service-time"]}},
                }
            ],
            "match": [
                {
                    "uri": {"prefix": "/"},
                }
            ],
        }
        http_list.append(http_ui)

        IstioVirtualService(
            payload=http_list, tenant=penknife.tenant, domain_name=config.penknife.domain_name, product=ProductName
        ).put()

        # penknife-careers istio config
        careers_http_list = []
        # http_api router
        careers_http_api = {
            "name": "penknife-api",
            "route": [
                {
                    "destination": {
                        "host": f"penknife.{penknife.tenant}.svc.cluster.local",
                        "port": {"number": 8000},
                    },
                    "headers": {
                        "response": {"add": {"Strict-Transport-Security": "max-age=31536000;includeSubDomains;preload"}}
                    },
                }
            ],
            "match": [
                {"uri": {"regex": "^/careerportal/api/v1/.*"}},
                {"uri": {"regex": "^/public/api/v1/.*"}},
            ],
        }
        careers_http_list.append(careers_http_api)
        # http_ui router
        careers_http_ui = {
            "name": "penknife-ui-root",
            "route": [
                {
                    "destination": {
                        "host": "varnish-svc.varnish.svc.cluster.local",
                        "port": {"number": 80},
                    },
                    "headers": {"response": {"remove": ["x-envoy-upstream-service-time"]}},
                }
            ],
            "match": [
                {
                    "uri": {"prefix": "/"},
                }
            ],
        }
        careers_http_list.append(careers_http_ui)

        IstioVirtualService(
            payload=careers_http_list,
            tenant=penknife.tenant,
            domain_name=config.penknife.domain_name,
            product=ProductName,
            service_name=f"{ProductName.lower()}-careers-vs",
            host=f"{penknife.tenant}-careers.{config.penknife.domain_name}",
        ).put()


class StatefulSetPodCreationActivity(Activity):
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
    @activity.defn(name="StatefulSetPodCreationActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        # Deploy k8s deployment
        from kubernetes.client.models import V1VolumeMount, V1Volume, V1EnvVar, V1ConfigMapVolumeSource, V1KeyToPath

        from app.cli.activities.statefulSetPodCreation import StatefulSetPodCreation
        from app.core.settings import get_settings

        environment = get_settings().env
        image_tag = "production" if environment == "production" else "sprint"
        docker_image = f"registry.314ecorp.tech/penknife-app:{image_tag}"

        volume_mounts = [
            V1Volume(
                name="tenant-volume",
                config_map=V1ConfigMapVolumeSource(
                    name="penknife-tenant-config",
                    items=[V1KeyToPath(key="tenant-config.json", path="tenant-config.json")],
                ),
            ),
            V1Volume(
                name="statestore-volume",
                config_map=V1ConfigMapVolumeSource(
                    name="penknife-statestore-config",
                    items=[V1KeyToPath(key="statestore.yaml", path="statestore.yaml")],
                ),
            ),
        ]

        volumes = [
            V1Volume(
                name="tenant-volume",
                config_map=V1ConfigMapVolumeSource(
                    name="penknife-tenant-config",
                    items=[V1KeyToPath(key="tenant-config.json", path="tenant-config.json")],
                ),
            ),
            V1Volume(
                name="statestore-volume",
                config_map=V1ConfigMapVolumeSource(
                    name="penknife-statestore-config",
                    items=[V1KeyToPath(key="statestore.yaml", path="statestore.yaml")],
                ),
            ),
        ]

        environment_variables = [
            V1EnvVar(name="DEPLOYMENT", value=environment),
            V1EnvVar(name="APP_CONFIG_FILE", value="/config/tenant-config.json"),
            V1EnvVar(name="IS_CLI", value="FALSE"),
            V1EnvVar(name="WEB_CONCURRENCY", value="5"),
            V1EnvVar(name="EXTRACTOR_ENABLED", value="FALSE"),
        ]

        StatefulSetPodCreation(
            tenant=penknife.tenant,
            name="penknife",
            docker_image=docker_image,
            request_resource={"cpu": penknife.serverSpec.request_cpu, "memory": penknife.serverSpec.request_memory},
            limit_resource={"cpu": penknife.serverSpec.limit_cpu, "memory": penknife.serverSpec.limit_memory},
            container_ports=[8000],
            volume_mounts=volume_mounts,
            volumes=volumes,
            container_envs=environment_variables,
        ).put()

        volume_mounts.append(V1VolumeMount(name="vector-volume", mount_path="/vector", read_only=True))

        environment_variables = [
            V1EnvVar(name="DEPLOYMENT", value=environment),
            V1EnvVar(name="APP_CONFIG_FILE", value="/config/tenant-config.json"),
            V1EnvVar(name="IS_CLI", value="TRUE"),
            V1EnvVar(name="IS_TEMPORAL_WORKER", value="TRUE"),
            V1EnvVar(name="VECTOR_LOG", value="off"),
            V1EnvVar(name="EXTRACTOR_ENABLED", value="TRUE"),
        ]

        volumes.append(
            V1Volume(
                name="vector-volume",
                config_map=V1ConfigMapVolumeSource(
                    name="penknife-cli-vector-config",
                    items=[V1KeyToPath(key="vector-config.toml", path="vector-config.toml")],
                ),
            )
        )

        StatefulSetPodCreation(
            tenant=penknife.tenant,
            name="penknife-cli",
            docker_image=docker_image,
            request_resource={"cpu": penknife.serverSpec.request_cpu, "memory": penknife.serverSpec.request_memory},
            limit_resource={"cpu": penknife.serverSpec.limit_cpu, "memory": penknife.serverSpec.limit_memory},
            container_ports=[8000],
            volume_mounts=volume_mounts,
            volumes=volumes,
            container_envs=environment_variables,
        ).put()


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
        from app.cli.activities.vmPodScraper import VMPodScrapperServer

        name = "penknife-metrics"

        VMPodScrapperServer(tenant=penknife.tenant, product=ProductName, name=name).put()


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
        from app.cli.activities.tenantStatus import update_tenant_status
        from app.cli.temporal.penknife.penknife import ProductName
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
        from app.cli.activities.temporalNamespaceCreation import TemporalNamespaceCreation

        temporal_namespace = f"jeeves_{penknife.tenant}"

        await TemporalNamespaceCreation(namespace=temporal_namespace).create_temporal_namespace()


class SetupUserActivity(Activity):
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
    @activity.defn(name="SetupUserActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        import orjson
        from app.cli.activities.penknifeNovuSetup import NovuSetup
        from app.cli.activities.penknifeKeycloakSetup import get_keycloak_user_id
        from app.core.db import DBManager, get_db_manager
        from app.core.settings import PenknifeSettings, get_settings
        from loguru import logger
        from datetime import datetime
        from app.cli.temporal.core.log import log_info

        subscriber_id = str(uuid4())

        NovuSetup(penknife=penknife).create_subscriber_in_novu(subscriber_id=subscriber_id)

        keycloak_user_id = await get_keycloak_user_id(penknife=penknife)
        penknife_config: PenknifeSettings = get_settings().penknife

        try:
            db: DBManager = await get_db_manager(dsn=penknife_config.postgres.dsn)
            attributes = orjson.dumps({"email": penknife.email}).decode("utf-8")
            await db.execute_raw_sql("""SELECT set_config('myvars.user_email', 'api@penknife.app', false);""")
            await db.fetch_one(
                sqlfile="penknife/insertSubscriptionmapping.sql",
                db_schema_name=penknife.tenant,
                **{
                    "schema": penknife.tenant,
                    "user_id": keycloak_user_id,
                    "subscriber_id": subscriber_id,
                    "attributes": attributes,
                },
            )
            await db.fetch_one(
                sqlfile="penknife/insertUseraudit.sql",
                db_schema_name=penknife.tenant,
                **{"schema": penknife.tenant, "email": penknife.email, "datetime": datetime.now()},
            )
            await db.fetch_one(
                sqlfile="penknife/updateOrganization.sql",
                db_schema_name=penknife.tenant,
                **{"schema": penknife.tenant, "companydomain": penknife.companyDomain},
            )

            log_info("User detail is added to postgres")

        except Exception as e:
            logger.error(f"Error while updating user entry in useraudit: {e}")
            raise e


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

        from app.cli.activities.mail import send_provisioning_mail
        from app.core.settings import PenknifeSettings, get_settings

        penknife_config: PenknifeSettings = get_settings().penknife

        await send_provisioning_mail(
            realm_name=penknife.tenant,
            tenant=penknife.tenant,
            user_details={"firstName": penknife.firstName, "lastName": penknife.lastName, "email": penknife.email},
            domain_name=penknife_config.domain_name,
            product=ProductName,
            from_name=penknife_config.sender_name,
            email_from=penknife_config.sender_email,
        )
