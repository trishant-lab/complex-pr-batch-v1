import dataclasses
from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity
from app.cli.temporal.dexit.dexit import DexitSpec

ProductName = "dexit"
OnePasswordVault = "Dexit"


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
    async def defn(dexit: DexitSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.activities.postgresSchemaSetup import setup_postgres
        from app.cli.temporal.dexit import TemplatePath
        from app.core.settings import get_settings

        database_name = "dexit"
        schema_name = dexit.tenant
        vault_name = "Dexit"

        await setup_postgres(
            tenant=dexit.tenant,
            product_name=ProductName,
            schema_name=schema_name,
            database_name=database_name,
            vault_name=vault_name,
            template_path=TemplatePath,
            config=get_settings().dexit,
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
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="namespace_setup_activity")
    async def defn(dexit: DexitSpec) -> None:
        """
        Callable for the activity
        """
        # create namespace in k8s
        from app.cli.activities.namespaceSetup import Namespace

        Namespace(tenant=dexit.tenant).put()


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
    async def defn(dexit: DexitSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.activities.configMapSetup import ConfigMapClass

        tenant_config: dict[str, str] = {"name": "dexit-tenant-config", "key": "tenant-config.json"}
        rclone_config: dict[str, str] = {"name": "dexit-env-config", "key": "env-config.json"}
        vector_config: dict[str, str] = {"name": "dexit-cli-vector-config", "key": "vector-config.toml"}

        bucket_name = "dexit-config"

        ConfigMapClass(tenant=dexit.tenant, config_map=tenant_config, bucket_name=bucket_name).put()
        ConfigMapClass(tenant=dexit.tenant, config_map=rclone_config, bucket_name=bucket_name).put()
        ConfigMapClass(tenant=dexit.tenant, config_map=vector_config, bucket_name=bucket_name).put()


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
    async def defn(dexit: DexitSpec) -> None:
        """
        Callable for the activity
        """
        # create secret in k8s for namespace
        from app.cli.activities.secretSetup import Secret
        from app.core.settings import get_settings, AppSettings

        config: AppSettings = get_settings()

        # Create registry secret for pulling images
        Secret(
            tenant=dexit.tenant,
            name="registrycred",
            type="kubernetes.io/dockerconfigjson",
            data={".dockerconfigjson": config.docker_image_pull_secret},
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
    async def defn(dexit: DexitSpec) -> None:
        """
        Callable for the activity
        """
        # Create DNS
        from app.cli.activities.dnsSetup import dns_setup
        from app.core.settings import get_settings, AppSettings

        config: AppSettings = get_settings()

        fqdn = f"{dexit.tenant}.{config.dexit.domain_name}."

        await dns_setup(google_dns_cname=config.google_dns_cname, fqdn=fqdn, zone_name=config.dexit.zone_name)


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
    async def defn(dexit: DexitSpec) -> None:
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
            dest_dir = f"{dexit.tenant}.{config.dexit.domain_name}/"
        else:
            dest_dir = f"{dexit.tenant}.{config.dexit.domain_name}/{image_tag}"

        repo_name = "dexit-ui"

        src_object_name = f"{repo_name}/{image_tag}/bundle.zip"

        UISetup(src_object_name=src_object_name, dest_dir=dest_dir).deploy()


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
    async def defn(dexit: DexitSpec) -> None:
        """
        Callable for the activity
        """
        # Deploy keycloak
        import os
        from app.cli.activities.keycloakSetup import create_realm_and_users
        from app.cli.temporal.dexit import TemplatePath

        user_details = {
            "username": dexit.email,
            "email": dexit.email,
            "firstname": dexit.firstName,
            "lastname": dexit.lastName,
        }
        environment: str = os.getenv("DEPLOYMENT", "integration").lower()
        domain = "com" if environment == "production" else "tech"

        roles = [
            "_standalone-launch",
            "_document-read",
            "_delete-document",
            "_document-indexing",
            "_document-commit",
            "_manage-document-type",
            "_manage-deficiency",
            "_manage-users",
            "_manage-organisation",
            "_manage-document-type",
            "_manage-queues",
            "_manage-subscription",
            "_manage-faxes",
            "_manage-bulk-import",
            "_roi",
            "_reports",
            "_document-review",
        ]

        await create_realm_and_users(
            tenant=dexit.tenant,
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
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="novu_setup_activity")
    async def defn(dexit: DexitSpec) -> None:
        """
        Callable for the activity
        """
        # Setup novu
        from app.cli.activities.dexitNovuSetup import NovuSetup

        NovuSetup(dexit=dexit).setup_novu()


class FaxSetupActivity(Activity):
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
    @activity.defn(name="fax_setup_activity")
    async def defn(dexit: DexitSpec) -> None:
        """
        Callable for the activity
        """
        # Setup fax
        from app.cli.activities.faxSetup import FaxSetup

        await FaxSetup(dexit=dexit).setup_fax()


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
    async def defn(dexit: DexitSpec) -> None:
        """
        Callable for the activity
        """
        # Check provisioning status
        from kubernetes.client import V1VolumeMount, V1Volume, V1ConfigMapVolumeSource, V1KeyToPath, V1EnvVar

        from app.cli.activities.databaseMigrationJob import DatabaseMigrationJob
        from app.onepasswordutil import OnePasswordUtil
        from app.core.settings import get_settings

        postgres_user = f"dexit_{dexit.tenant}"
        postgres_password = OnePasswordUtil(
            tenant=f"Dexit_{dexit.tenant}",
            server_item="application-config",
            vault=OnePasswordVault,
        ).get_key("pg_password")
        image_tag = "production" if get_settings().env == "production" else "sprint"
        docker_image = f"registry.314ecorp.tech/dexit-app:{image_tag}"

        volume_mounts = [
            V1VolumeMount(
                name="dexit-env-config",
                mount_path="/config/env-config.json",
                sub_path="env-config.json",
                read_only=True,
            ),
            V1VolumeMount(
                name="dexit-tenant-config",
                mount_path="/config/tenant-config.json",
                sub_path="tenant-config.json",
                read_only=True,
            ),
        ]

        volumes = [
            V1Volume(
                name="dexit-env-config",
                config_map=V1ConfigMapVolumeSource(
                    name="dexit-env-config",
                    items=[V1KeyToPath(key="env-config.json", path="env-config.json")],
                ),
            ),
            V1Volume(
                name="dexit-tenant-config",
                config_map=V1ConfigMapVolumeSource(
                    name="dexit-tenant-config",
                    items=[V1KeyToPath(key="tenant-config.json", path="tenant-config.json")],
                ),
            ),
        ]

        envs = [
            V1EnvVar(name="POSTGRES_PASSWORD", value=postgres_password),
            V1EnvVar(name="POSTGRES_USER", value=postgres_user),
            V1EnvVar(name="APP_CONFIG_DIR", value="/config"),
            V1EnvVar(name="DEPLOYMENT", value=get_settings().env),
            V1EnvVar(name="CLIENT_CODE", value=dexit.tenant),
        ]

        database_migration_job = DatabaseMigrationJob(
            tenant=dexit.tenant,
            product=ProductName,
            job_name="dexit-atlas-migration-job",
            postgres_user=postgres_user,
            postgres_password=postgres_password,
            docker_image=docker_image,
            volume_mounts=volume_mounts,
            volumes=volumes,
            container_envs=envs,
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
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="kubernetes_service_activity")
    async def defn(dexit: DexitSpec) -> None:
        """
        Callable for the activity
        """
        # Create k8s service
        from app.cli.activities.serviceSetup import Service

        Service(tenant=dexit.tenant, product=ProductName, port=8000).put()


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
    async def defn(dexit: DexitSpec) -> None:
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
            "name": "dexit-api",
            "route": [
                {
                    "destination": {
                        "host": f"dexit.{dexit.tenant}.svc.cluster.local",
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
            "name": "dexit-log-collect",
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
            "name": "dexit-ui",
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
            payload=http_list, tenant=dexit.tenant, domain_name=config.dexit.domain_name, product=ProductName
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
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="StatefulSetPodCreationActivity")
    async def defn(dexit: DexitSpec) -> None:
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
        docker_image = f"registry.314ecorp.tech/dexit-app:{image_tag}"

        volume_mounts = [
            V1VolumeMount(
                name="env-volume",
                mount_path="/config/env-config.json",
                sub_path="env-config.json",
            ),
            V1VolumeMount(
                name="tenant-volume",
                mount_path="/config/tenant-config.json",
                sub_path="tenant-config.json",
            ),
        ]

        postgres_user = f"dexit_{dexit.tenant}"
        postgres_password = OnePasswordUtil(
            tenant=f"Dexit_{dexit.tenant}",
            server_item="application-config",
            vault=OnePasswordVault,
        ).get_key("pg_password")
        tika_server_endpoint = get_settings().dexit.tika_server_endpoint

        environment_variables = [
            V1EnvVar(name="DEPLOYMENT", value=environment),
            V1EnvVar(name="WEB_CONCURRENCY", value="5"),
            V1EnvVar(name="POSTGRES_PASSWORD", value=postgres_password),
            V1EnvVar(name="POSTGRES_USER", value=postgres_user),
            V1EnvVar(
                name="RELEASE_VERSION",
                value=image_tag,
            ),
            V1EnvVar(name="APP_CONFIG_DIR", value="/config"),
            V1EnvVar(name="CLIENT_CODE", value=dexit.tenant),
            V1EnvVar(name="TIKA_SERVER_ENDPOINT", value=tika_server_endpoint),
            V1EnvVar(name="CLI", value="FALSE"),
        ]

        volumes = [
            V1Volume(
                name="env-volume",
                config_map=V1ConfigMapVolumeSource(
                    name="dexit-env-config",
                    items=[V1KeyToPath(key="env-config.json", path="env-config.json")],
                ),
            ),
            V1Volume(
                name="tenant-volume",
                config_map=V1ConfigMapVolumeSource(
                    name="dexit-tenant-config",
                    items=[V1KeyToPath(key="tenant-config.json", path="tenant-config.json")],
                ),
            ),
        ]

        # server pod
        StatefulSetPodCreation(
            tenant=dexit.tenant,
            name="dexit",
            docker_image=docker_image,
            request_resource={"cpu": dexit.serverSpec.request_cpu, "memory": dexit.serverSpec.request_memory},
            limit_resource={"cpu": dexit.serverSpec.limit_cpu, "memory": dexit.serverSpec.limit_memory},
            container_ports=[8000],
            volume_mounts=volume_mounts,
            volumes=volumes,
            container_envs=environment_variables,
        ).put()

        # worker pod
        volume_mounts.append(V1VolumeMount(name="vector-volume", mount_path="/vector", read_only=True))

        environment_variables = [
            V1EnvVar(name="DEPLOYMENT", value=environment),
            V1EnvVar(name="POSTGRES_PASSWORD", value=postgres_password),
            V1EnvVar(name="POSTGRES_USER", value=postgres_user),
            V1EnvVar(name="RELEASE_VERSION", value=image_tag),
            V1EnvVar(name="APP_CONFIG_DIR", value="/config"),
            V1EnvVar(name="CLIENT_CODE", value=dexit.tenant),
            V1EnvVar(name="TIKA_SERVER_ENDPOINT", value=get_settings().dexit.tika_server_endpoint),
            V1EnvVar(name="CLI", value="TRUE"),
        ]

        volumes.append(
            V1Volume(
                name="vector-volume",
                config_map=V1ConfigMapVolumeSource(
                    name="dexit-cli-vector-config",
                    items=[V1KeyToPath(key="vector-config.toml", path="vector-config.toml")],
                ),
            )
        )

        StatefulSetPodCreation(
            tenant=dexit.tenant,
            name="dexit-worker",
            docker_image=docker_image,
            request_resource={"cpu": dexit.cliSpec.request_cpu, "memory": dexit.cliSpec.request_memory},
            limit_resource={"cpu": dexit.cliSpec.limit_cpu, "memory": dexit.cliSpec.limit_memory},
            container_ports=[8000],
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
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="vm_pod_scraper_activity")
    async def defn(dexit: DexitSpec) -> None:
        """
        Callable for the activity
        """
        # Scrape pod logs

        from app.cli.activities.vmPodScraper import VMPodScrapperServer

        name = "dexit-metrics"

        VMPodScrapperServer(tenant=dexit.tenant, product=ProductName, name=name).put()


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
    async def defn(dexit: DexitSpec) -> None:
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
    async def defn(activity_input: TenantStatus) -> None:
        """
        Callable for the activity
        """
        # Update tenant status
        from app.cli.activities.tenantStatus import update_tenant_status
        from app.models.tenant import TenantStatusEnum
        from app.cli.temporal.dexit.dexit import ProductName

        await update_tenant_status(
            tenant_name=activity_input.tenant_name,
            product=ProductName,
            status=TenantStatusEnum(activity_input.status),
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
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="temporal_namespace_creation_activity")
    async def defn(dexit: DexitSpec) -> None:
        """
        Callable for the activity
        """
        # Create temporal namespace
        from app.cli.activities.temporalNamespaceCreation import TemporalNamespaceCreation

        temporal_namespace = f"dexit_{dexit.tenant}"

        await TemporalNamespaceCreation(namespace=temporal_namespace).create_temporal_namespace()


class HFInferenceEndpointSetupActivity(Activity):
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
    @activity.defn(name="hf_inference_endpoint_setup_activity")
    async def defn(dexit: DexitSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.activities.hfinferenceendpoint import HFInferenceEndpointSetup

        await HFInferenceEndpointSetup(dexit=dexit).deploy()


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
    @activity.defn(name="send_mail_activity")
    async def defn(dexit: DexitSpec) -> None:
        """
        Callable for the activity
        """
        # Send mail to customer
        from app.cli.activities.mail import send_provisioning_mail
        from app.core.settings import get_settings

        await send_provisioning_mail(
            realm_name=dexit.tenant,
            tenant=dexit.tenant,
            user_details={"firstName": dexit.firstName, "lastName": dexit.lastName, "email": dexit.email},
            domain_name=get_settings().dexit.domain_name,
            product=ProductName,
            from_name="314e Support",
            email_from="developer@314ecorp.com",
        )
