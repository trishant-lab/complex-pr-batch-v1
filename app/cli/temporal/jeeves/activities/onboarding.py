import dataclasses
from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.jeeves.jeeves import JeevesSpec
from app.cli.temporal.core.base import Activity

ProductName = "jeeves"
OnePasswordVault = "Jeeves"


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
    async def defn(jeeves: JeevesSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.activities.postgresSetup import setup_postgres
        from app.cli.jeeves import TemplatePath
        from app.core.settings import get_settings

        database_name = "Jeeves"
        schema_name = jeeves.tenant
        vault_name = "Jeeves"

        await setup_postgres(
            tenant=jeeves.tenant,
            product_name=ProductName,
            schema_name=schema_name,
            database_name=database_name,
            vault_name=vault_name,
            template_path=TemplatePath,
            config=get_settings().jeeves,
            keycloak_db=True,
            matomo_db=True,
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
    async def defn(jeeves: JeevesSpec) -> None:
        """
        Callable for the activity
        """
        # create namespace in k8s
        from app.cli.activities.namespaceSetup import Namespace

        Namespace(tenant=jeeves.tenant).put()


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
    async def defn(jeeves: JeevesSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.activities.configMapSetup import ConfigMapClass

        tenant_config: dict[str, str] = {"name": "jeeves-tenant-config", "key": "tenant-config.json"}
        rclone_config: dict[str, str] = {"name": "jeeves-rclone-config", "key": "rclone.conf"}
        vector_config: dict[str, str] = {"name": "jeeves-cli-vector-config", "key": "vector-config.toml"}
        state_store_config: dict[str, str] = {"name": "jeeves-statestore-config", "key": "statestore.yaml"}

        bucket_name = "jeeves-config"

        ConfigMapClass(tenant=jeeves.tenant, config_map=tenant_config, bucket_name=bucket_name).put()
        ConfigMapClass(tenant=jeeves.tenant, config_map=rclone_config, bucket_name=bucket_name).put()
        ConfigMapClass(tenant=jeeves.tenant, config_map=vector_config, bucket_name=bucket_name).put()
        ConfigMapClass(tenant=jeeves.tenant, config_map=state_store_config, bucket_name=bucket_name).put()


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
    async def defn(jeeves: JeevesSpec) -> None:
        """
        Callable for the activity
        """
        # create secret in k8s for namespace
        from app.cli.activities.secretSetup import Secret
        from app.core.settings import get_settings, AppSettings

        config: AppSettings = get_settings()

        # Create registry secret for pulling images
        Secret(
            tenant=jeeves.tenant,
            name="registrycred",
            type="kubernetes.io/dockerconfigjson",
            data={".dockerconfigjson": config.docker_image_pull_secret},
        ).put()

        # Create redis secret for redis password
        Secret(
            tenant=jeeves.tenant,
            name="cache-secret",
            string_data={"REDIS_PASSWORD": config.cache_admin_password},
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
    async def defn(jeeves: JeevesSpec) -> None:
        """
        Callable for the activity
        """
        # create redisSetup set in k8s
        from app.cli.activities.redisSetup import RedisSetup

        await RedisSetup(tenant=jeeves.tenant, product=ProductName, vault_name="Jeeves").put()


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
    async def defn(jeeves: JeevesSpec) -> None:
        """
        Callable for the activity
        """
        # Create DNS
        from app.cli.activities.dnsSetup import dns_setup
        from app.core.settings import get_settings

        await dns_setup(
            tenant=jeeves.tenant, config=get_settings().jeeves, google_dns_cname=get_settings().google_dns_cname
        )


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
    async def defn(jeeves: JeevesSpec) -> None:
        """
        Callable for the activity
        """
        # Deploy ui
        from app.cli.activities.UISetup import UISetup
        from app.core.settings import get_settings

        UISetup(tenant=jeeves.tenant, domain_name=get_settings().jeeves.domain_name, repo_name="jeeves-ui").deploy()


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
    async def defn(jeeves: JeevesSpec) -> None:
        """
        Callable for the activity
        """
        # Deploy keycloak
        import os
        from app.cli.activities.keycloakSetup import create_realm_and_users
        from app.cli.jeeves import TemplatePath

        user_details = {
            "username": jeeves.email,
            "email": jeeves.email,
            "firstName": jeeves.firstName,
            "lastName": jeeves.lastName,
        }
        environment: str = os.getenv("DEPLOYMENT", "integration").lower()
        domain = "com" if environment == "production" else "tech"

        roles = [
            "_access-manage-todos",
            "_access-manage-alerts",
            "_access-settings",
            "_allow-delete-assets",
            "_allow-add-edit-assets",
            "_access-reports",
            "_allow-view-assets",
            "_JEEVESALL",
            "_allow-conversion-tools",
            "_developer",
            "_access-screen-recorder",
            "_allow-standalone-launch",
            "_allow-publish-assets",
            "_can-manage-activities",
            "_allow-add-edit-courses",
            "_allow-delete-courses",
            "_allow-enroll-courses",
            "_allow-view-all-courses",
        ]

        await create_realm_and_users(
            tenant=jeeves.tenant,
            user_details=user_details,
            product=ProductName,
            roles=roles,
            domain=domain,
            template_path=TemplatePath,
        )


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
    async def defn(jeeves: JeevesSpec) -> None:
        """
        Callable for the activity
        """
        # Setup novu
        from app.cli.activities.jeevesNovuSetup import NovuSetup

        NovuSetup(jeeves=jeeves).setup_novu()


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
    async def defn(jeeves: JeevesSpec) -> None:
        """
        Callable for the activity
        """
        # Check provisioning status
        from kubernetes.client import V1VolumeMount, V1Volume, V1ConfigMapVolumeSource, V1KeyToPath

        from app.cli.activities.databaseMigrationJob import DatabaseMigrationJob
        from app.cli.activities.vespaJob import VespaJob
        from app.onepasswordutil import OnePasswordUtil
        from app.core.settings import get_settings

        postgres_user = f"jeeves_{jeeves.tenant}"
        postgres_password = OnePasswordUtil(
            tenant=f"Jeeves_{jeeves.tenant}",
            server_item="application-config",
            vault=OnePasswordVault,
        ).get_key("pg_password")
        image_tag = "production" if get_settings().env == "production" else "sprint"
        docker_image = f"registry.314ecorp.tech/jeeves-app:{image_tag}"

        volume_mount = V1VolumeMount(
            name="jeeves-tenant-config",
            mount_path="/config/tenant-config.json",
            sub_path="tenant-config.json",
            read_only=True,
        )

        volume = V1Volume(
            name="jeeves-tenant-config",
            config_map=V1ConfigMapVolumeSource(
                name="jeeves-tenant-config",
                items=[V1KeyToPath(key="tenant-config.json", path="tenant-config.json")],
            ),
        )

        database_migration_job = DatabaseMigrationJob(
            tenant=jeeves.tenant,
            product=ProductName,
            job_name="jeeves-db-schema-migration-job",
            postgres_user=postgres_user,
            postgres_password=postgres_password,
            docker_image=docker_image,
            volume_mounts=[volume_mount],
            volumes=[volume],
        )
        database_migration_job.delete()
        database_migration_job.put()

        vespa_job = VespaJob(jeeves=jeeves)
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
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="KubernetesServiceActivity")
    async def defn(jeeves: JeevesSpec) -> None:
        """
        Callable for the activity
        """
        # Create k8s service
        from app.cli.activities.serviceSetup import Service

        Service(tenant=jeeves.tenant, product=ProductName).put()


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
    async def defn(jeeves: JeevesSpec) -> None:
        """
        Callable for the activity
        """
        # Create k8s virtual service
        from app.cli.activities.istioVirtualService import IstioVirtualService
        from app.core.settings import get_settings, AppSettings

        config: AppSettings = get_settings()
        env = config.env
        image_tag = "sprint" if env == "integration" else "production"

        http_list = []

        # http_api router
        http_api = {
            "name": "jeeves-api",
            "route": [
                {
                    "destination": {
                        "host": f"jeeves.{jeeves.tenant}.svc.cluster.local",
                        "port": {"number": 8000},
                    },
                    "headers": {
                        "response": {
                            "add": {
                                "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
                            }
                        }
                    },
                }
            ],
            "match": [
                {"uri": {"regex": "^/api/v1/.*"}},
                {"uri": {"regex": "^/public/api/v1/.*"}},
                {"uri": {"prefix": "/docs"}},
                {"uri": {"prefix": "/redoc"}},
            ],
        }
        http_list.append(http_api)

        # http_log_collect router
        http_log_collect = {
            "name": "jeeves-log-collect",
            "route": [
                {
                    "destination": {
                        "host": "grafana-agent.monitoring-system.svc.cluster.local",
                        "port": {"number": 12347},
                    }
                }
            ],
            "match": [
                {
                    "uri": {"prefix": "/logcollect"},
                }
            ],
            "rewrite": {"uri": "/collect"},
        }
        http_list.append(http_log_collect)

        # http analytics router
        http_analytics = {
            "name": "jeeves-analytics",
            "route": [
                {
                    "destination": {
                        "host": "matomo-server.matomo.svc.cluster.local",
                        "port": {"number": 80},
                    }
                }
            ],
            "match": [
                {
                    "uri": {"prefix": "/insights/"},
                }
            ],
            "rewrite": {"uri": "/"},
        }
        http_list.append(http_analytics)

        # http alerting router
        http_alerting = {
            "name": "jeeves-alerting",
            "route": [
                {
                    "destination": {
                        "host": "api.novu.svc.cluster.local",
                        "port": {"number": 4000},
                    }
                }
            ],
            "match": [
                {
                    "uri": {"prefix": "/alerting/"},
                }
            ],
            "rewrite": {"uri": "/"},
        }
        http_list.append(http_alerting)

        # novu socket router
        novu_socket = {
            "name": "novu-socket",
            "route": [
                {
                    "destination": {
                        "host": "ws.novu.svc.cluster.local",
                        "port": {"number": 3002},
                    }
                }
            ],
            "match": [
                {
                    "uri": {"prefix": "/socket.io/"},
                }
            ],
        }
        http_list.append(novu_socket)

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
            "name": "jeeves-ui",
            "route": [
                {
                    "destination": {
                        "host": "varnish-svc.varnish.svc.cluster.local",
                        "port": {"number": 80},
                    }
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
            payload=http_list, tenant=jeeves.tenant, domain_name=config.jeeves.domain_name, product=ProductName
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
    async def defn(jeeves: JeevesSpec) -> None:
        """
        Callable for the activity
        """
        # Deploy k8s deployment
        from kubernetes.client.models import V1VolumeMount, V1Volume, V1EnvVar, V1ConfigMapVolumeSource, V1KeyToPath

        from app.cli.activities.statefulSetPodCreation import StatefulSetPodCreation
        from app.onepasswordutil import OnePasswordUtil
        from app.core.settings import get_settings

        environment = get_settings().env
        image_tag = "production" if environment == "production" else "sprint"
        docker_image = f"registry.314ecorp.tech/jeeves-app:{image_tag}"

        volume_mounts = [
            V1VolumeMount(
                name="tenant-volume",
                mount_path="/config/tenant-config.json",
                sub_path="tenant-config.json",
            ),
            V1VolumeMount(name="rclone-volume", mount_path="/root/.config/rclone/", read_only=True),
            V1VolumeMount(
                name="statestore-volume",
                mount_path="/root/.dapr/components/statestore.yaml",
                sub_path="statestore.yaml",
            ),
        ]

        dynamic_url_hash_key = OnePasswordUtil(
            tenant="PRODUCTION_COMMON_CONFIG" if environment == "production" else "INTEGRATION_COMMON_CONFIG",
            server_item="application-config",
            vault=OnePasswordVault,
        ).get_key("dynamic_url_hash_key")

        postgres_user = f"jeeves_{jeeves.tenant}"
        postgres_password = OnePasswordUtil(
            tenant=f"Jeeves_{jeeves.tenant}",
            server_item="application-config",
            vault=OnePasswordVault,
        ).get_key("pg_password")

        environment_variables = [
            V1EnvVar(name="DEPLOYMENT", value=environment),
            V1EnvVar(name="WEB_CONCURRENCY", value="5"),
            V1EnvVar(name="CLIENT_CODE", value=jeeves.tenant),
            V1EnvVar(name="APP_CONFIG_FILE", value="/config/tenant-config.json"),
            V1EnvVar(name="POSTGRES_PASSWORD", value=postgres_password),
            V1EnvVar(name="POSTGRES_USER", value=postgres_user),
            V1EnvVar(name="EXTRACTOR_ENABLED", value="FALSE"),
            V1EnvVar(name="TIKA_SERVER_ENDPOINT", value=get_settings().jeeves.tika_server_endpoint),
            V1EnvVar(name="DYNAMIC_URL_HASH_KEY", value=dynamic_url_hash_key),
            V1EnvVar(name="DYNAMIC_URL_ENABLED", value="True"),
        ]

        volumes = [
            V1Volume(
                name="tenant-volume",
                config_map=V1ConfigMapVolumeSource(
                    name="jeeves-tenant-config",
                    items=[V1KeyToPath(key="tenant-config.json", path="tenant-config.json")],
                ),
            ),
            V1Volume(
                name="rclone-volume",
                config_map=V1ConfigMapVolumeSource(
                    name="jeeves-rclone-config",
                    items=[V1KeyToPath(key="rclone.conf", path="rclone.conf")],
                ),
            ),
            V1Volume(
                name="statestore-volume",
                config_map=V1ConfigMapVolumeSource(
                    name="jeeves-statestore-config",
                    items=[V1KeyToPath(key="statestore.yaml", path="statestore.yaml")],
                ),
            ),
        ]

        # server pod
        StatefulSetPodCreation(
            tenant=jeeves.tenant,
            name="jeeves",
            docker_image=docker_image,
            request_resource={"cpu": jeeves.serverSpec.request_cpu, "memory": jeeves.serverSpec.request_memory},
            limit_resource={"cpu": jeeves.serverSpec.limit_cpu, "memory": jeeves.serverSpec.limit_memory},
            container_port=8000,
            volume_mounts=volume_mounts,
            volumes=volumes,
            container_envs=environment_variables,
        ).put()

        # worker pod
        volume_mounts.append(V1VolumeMount(name="vector-volume", mount_path="/vector", read_only=True))

        environment_variables = [
            V1EnvVar(name="DEPLOYMENT", value=environment),
            V1EnvVar(name="CLIENT_CODE", value=jeeves.tenant),
            V1EnvVar(name="APP_CONFIG_FILE", value="/config/tenant-config.json"),
            V1EnvVar(name="POSTGRES_PASSWORD", value=postgres_password),
            V1EnvVar(name="POSTGRES_USER", value=postgres_user),
            V1EnvVar(name="EXTRACTOR_ENABLED", value="TRUE"),
            V1EnvVar(name="TIKA_SERVER_ENDPOINT", value=get_settings().jeeves.tika_server_endpoint),
            V1EnvVar(name="DYNAMIC_URL_HASH_KEY", value=dynamic_url_hash_key),
            V1EnvVar(name="DYNAMIC_URL_ENABLED", value="True"),
        ]

        volumes.append(
            V1Volume(
                name="vector-volume",
                config_map=V1ConfigMapVolumeSource(
                    name="jeeves-cli-vector-config",
                    items=[V1KeyToPath(key="vector-config.toml", path="vector-config.toml")],
                ),
            )
        )

        StatefulSetPodCreation(
            tenant=jeeves.tenant,
            name="jeeves-worker",
            docker_image=docker_image,
            request_resource={"cpu": jeeves.cliSpec.request_cpu, "memory": jeeves.cliSpec.request_memory},
            limit_resource={"cpu": jeeves.cliSpec.limit_cpu, "memory": jeeves.cliSpec.limit_memory},
            container_port=8000,
            volume_mounts=volume_mounts,
            container_envs=environment_variables,
            volumes=volumes,
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
    async def defn(jeeves: JeevesSpec) -> None:
        """
        Callable for the activity
        """
        # Scrape pod logs
        from app.cli.activities.vmPodScraper import VMPodScrapperServer

        name = "jeeves-metrics"

        VMPodScrapperServer(tenant=jeeves.tenant, product=ProductName, name=name).put()


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
        from app.cli.jeeves.jeeves import ProductName
        from app.models.tenant import TenantStatusEnum

        status = TenantStatusEnum(activity_input.status)

        await update_tenant_status(
            tenant_name=activity_input.tenant_name,
            product=ProductName,
            status=status,
            error_message=activity_input.error_msg,
        )


class ChatwootSetupActivity(Activity):
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
    @activity.defn(name="ChatwootSetupActivity")
    async def defn(jeeves: JeevesSpec) -> None:
        """
        Callable for the activity
        """
        # Setup chatwoot
        from app.cli.activities.chatwootSetup import ChatwootSetup
        from app.core.settings import get_settings

        ChatwootSetup(tenant=jeeves.tenant, product=ProductName, config=get_settings().jeeves).setup()


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
    async def defn(jeeves: JeevesSpec) -> None:
        """
        Callable for the activity
        """
        # Create temporal namespace
        from app.cli.activities.temporalNamespaceCreation import TemporalNamespaceCreation

        temporal_namespace = f"jeeves_{jeeves.tenant}"

        await TemporalNamespaceCreation(namespace=temporal_namespace).create_temporal_namespace()


class AiVoiceSetupActivity(Activity):
    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=2,
        )

    @staticmethod
    @activity.defn(name="AiVoiceSetupActivity")
    async def defn(jeeves: JeevesSpec) -> None:
        """
        Callable for the activity
        """
        # Add AI voices to storage
        from app.cli.activities.aiVoiceSetup import add_ai_voices_to_storage
        from app.core.settings import get_settings

        add_ai_voices_to_storage(tenant=jeeves.tenant, config=get_settings().jeeves)


class BeforeProvisioningMailActivity(Activity):
    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=2,
        )

    @staticmethod
    @activity.defn(name="BeforeProvisioningMailActivity")
    async def defn(jeeves: JeevesSpec) -> None:
        """
        Callable for the activity
        """
        # Send mail to customer
        from app.cli.activities.mail import send_before_provisioning_mail

        await send_before_provisioning_mail(
            user_details={"firstName": jeeves.firstName, "lastName": jeeves.lastName, "email": jeeves.email},
            product=ProductName,
            from_name="Jeeves Support",
            email_from="support@okjeeves.com",
        )


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
    async def defn(jeeves: JeevesSpec) -> None:
        """
        Callable for the activity
        """
        # Send mail to customer

        from app.cli.activities.mail import send_provisioning_mail
        from app.core.settings import get_settings

        await send_provisioning_mail(
            realm_name=jeeves.tenant,
            tenant=jeeves.tenant,
            user_details={"firstName": jeeves.firstName, "lastName": jeeves.lastName, "email": jeeves.email},
            domain_name=get_settings().jeeves.domain_name,
            product=ProductName,
            from_name="Jeeves Support",
            email_from="support@okjeeves.com",
        )


class PreLoadAssetsJobActivity(Activity):
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
    @activity.defn(name="PreLoadAssetsJobActivity")
    async def defn(jeeves: JeevesSpec) -> None:
        """
        Callable for the activity
        """
        # Preload assets
        from app.cli.activities.preLoadAssetsJob import PreLoadAssetsJob

        await PreLoadAssetsJob(jeeves=jeeves).put()
