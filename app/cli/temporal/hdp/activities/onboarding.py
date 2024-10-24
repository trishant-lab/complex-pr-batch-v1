import dataclasses
from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.hdp.models.hdpSpec import HDPSpec
from app.cli.temporal.core.base import Activity

ProductName = "hdp"
OnePasswordVault = "HDP"
vault_name = "hdp"


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
    async def defn(hdp: HDPSpec) -> None:
        """
        Callable for the activity
        """
        from app.cli.activities.postgresDatabaseCreation import setup_postgres_database
        from app.core.settings import get_settings

        await setup_postgres_database(
            tenant=hdp.tenant,
            product_name=ProductName,
            database_name=f"{ProductName.lower()}_{hdp.tenant}",
            db_username=f"{ProductName.lower()}_{hdp.tenant}",
            vault_name=vault_name,
            config=get_settings(),
            vault_key_name=f"{ProductName.lower()}_pg_password",
        )

        # create postgres database for kestra
        await setup_postgres_database(
            tenant=hdp.tenant,
            product_name=ProductName,
            database_name=f"kestra_{hdp.tenant}",
            db_username=f"kestra_{hdp.tenant}",
            vault_name=vault_name,
            config=get_settings(),
            vault_key_name="kestra_pg_password",
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
    async def defn(hdp: HDPSpec) -> None:
        """
        Callable for the activity
        """
        # create namespace in k8s
        from app.cli.activities.namespaceSetup import Namespace

        Namespace(tenant=hdp.tenant).put()


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
    async def defn(hdp: HDPSpec) -> None:
        """
        Callable for the activity
        """
        pass
        from app.cli.activities.configMapSetup import ConfigMapClass
        from app.common import generate_password
        from app.onepasswordutil import OnePasswordUtil

        tenant_config: dict[str, str] = {"name": "hdp-tenant-config", "key": "tenant-config.json"}
        kestra_config: dict[str, str] = {"name": "kestra-config", "key": "kestra-config.yml"}

        bucket_name = "hdp-config"

        kestra_password = generate_password(20)
        OnePasswordUtil(
            tenant=f"HDP_{hdp.tenant}",
            server_item="application-config",
            vault=OnePasswordVault,
        ).create_or_replace("kestra_password", kestra_password)

        ConfigMapClass(tenant=hdp.tenant, config_map=tenant_config, bucket_name=bucket_name).put()
        ConfigMapClass(tenant=hdp.tenant, config_map=kestra_config, bucket_name=bucket_name).put()


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
    async def defn(hdp: HDPSpec) -> None:
        """
        Callable for the activity
        """
        # create secret in k8s for namespace
        from app.cli.activities.secretSetup import Secret
        from app.core.settings import get_settings, AppSettings

        config: AppSettings = get_settings()

        # Create registry secret for pulling images
        Secret(
            tenant=hdp.tenant,
            name="registrycred",
            type="kubernetes.io/dockerconfigjson",
            data={".dockerconfigjson": config.docker_image_pull_secret},
        ).put()

        # Create redis secret for redis password
        Secret(
            tenant=hdp.tenant,
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
    async def defn(hdp: HDPSpec) -> None:
        """
        Callable for the activity
        """
        # create redisSetup set in k8s
        from app.cli.activities.redisSetup import RedisSetup

        await RedisSetup(tenant=hdp.tenant, product=ProductName, vault_name="hdp").put()


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
    async def defn(hdp: HDPSpec) -> None:
        """
        Callable for the activity
        """
        # Create DNS
        from app.cli.activities.dnsSetup import dns_setup
        from app.core.settings import get_settings, AppSettings

        config: AppSettings = get_settings()

        fqdn = f"{hdp.tenant}.{config.hdp.domain_name}."

        await dns_setup(google_dns_cname=config.google_dns_cname, fqdn=fqdn, zone_name=config.hdp.zone_name)


# HDP UI
# TODO: create one more for superset
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
    async def defn(hdp: HDPSpec) -> None:
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
            dest_dir = f"{hdp.tenant}.{config.hdp.domain_name}/"
        else:
            dest_dir = f"{hdp.tenant}.{config.hdp.domain_name}/{image_tag}"

        repo_name = "hdp-ui"

        src_object_name = f"{repo_name}/{image_tag}/bundle.zip"

        UISetup(src_object_name=src_object_name, dest_dir=dest_dir, product_name=ProductName).deploy()


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
    async def defn(hdp: HDPSpec) -> None:
        """
        Callable for the activity
        """
        # Deploy keycloak
        import os
        from app.cli.activities.keycloakSetup import create_realm_and_users
        from app.cli.temporal.hdp import TemplatePath

        user_details = {
            "username": hdp.email,
            "email": hdp.email,
            "firstName": hdp.firstName,
            "lastName": hdp.lastName,
        }
        environment: str = os.getenv("DEPLOYMENT", "integration").lower()
        domain = "com" if environment == "production" else "tech"

        roles = [
            "_hdpdashboard_edit_dashboard",
            "_can-export-dashboard",
            "_hdpdashboard_view_charts",
            "_can-export-database",
            "_hdpdashboard_view_sql",
            "_can-export-dataset",
            "_can-modify-user-access",
            "_can-modify-dashboard-settings",
            "_hdpdashboard_engineer_sql",
            "_can-modify-general-settings",
            "_hdpdashboard_edit_dataset",
            "_can-delete-charts",
            "_can-delete-database",
            "_can-export-charts",
            "_hdpdashboard_edit_database",
            "_hdpdashboard_view_extracts",
            "_can-view-streamline",
            "_can-delete-extracts",
            "_hdpdashboard_edit_charts",
            "_hdpdashboard_view_dashboard",
            "_hdpdashboard_view_database",
            "_hdpdashboard_edit_extracts",
            "_can-export-extracts",
            "_can-engineer-streamline",
            "_hdpdashboard_Admin",
            "_hdpdashboard_view_dataset",
            "_can-delete-dataset",
        ]

        await create_realm_and_users(
            tenant=hdp.tenant,
            user_details=user_details,
            product=ProductName,
            roles=roles,
            domain=domain,
            template_path=TemplatePath,
        )


# K8s setup
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
    async def defn(hdp: HDPSpec) -> None:
        """
        Callable for the activity
        """
        # Create k8s service
        from app.cli.activities.serviceSetup import Service

        Service(tenant=hdp.tenant, product=ProductName, port=8000).put()


# TODO: Work with Devops to complete this
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
    async def defn(hdp: HDPSpec) -> None:
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
            "name": "hdp-api",
            "route": [
                {
                    "destination": {
                        "host": f"hdp.{hdp.tenant}.svc.cluster.local",
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
            "name": "hdp-ui",
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
            payload=http_list, tenant=hdp.tenant, domain_name=config.hdp.domain_name, product=ProductName
        ).put()


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
    async def defn(hdp: HDPSpec) -> None:
        """
        Callable for the activity
        """
        # Create k8s persistent volume claim
        from app.cli.activities.pvcSetup import PVC
        from app.core.settings import get_settings

        env = get_settings().env

        PVC(tenant=hdp.tenant, pvc_name="hdp-volume", env=env).put()


# TODO: Needs update
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
    async def defn(hdp: HDPSpec) -> None:
        """
        Callable for the activity
        """
        # Deploy k8s deployment
        from kubernetes.client.models import (
            V1VolumeMount,
            V1Volume,
            V1EnvVar,
            V1ConfigMapVolumeSource,
            V1KeyToPath,
            V1PersistentVolumeClaimVolumeSource,
        )
        from kubernetes.client import V1Container

        from app.cli.activities.statefulSetPodCreation import StatefulSetPodCreation

        from app.onepasswordutil import OnePasswordUtil
        from app.core.settings import get_settings
        from app.common import generate_password

        environment = get_settings().env
        image_tag = "production" if environment == "production" else "sprint"
        docker_image = f"registry.314ecorp.tech/hdp-api:{image_tag}"

        postgres_password = OnePasswordUtil(
            tenant=f"HDP_{hdp.tenant}",
            server_item="application-config",
            vault=OnePasswordVault,
        ).get_key(f"hdp_{hdp.tenant}_pg_password")

        redis_password = OnePasswordUtil(
            tenant=f"HDP_{hdp.tenant}",
            server_item="application-config",
            vault=OnePasswordVault,
        ).get_key("redis_password")

        volume_mounts = [
            V1VolumeMount(
                name="tenant-volume",
                mount_path="/config/tenant-config.json",
                sub_path="tenant-config.json",
            ),
            V1VolumeMount(name="hdp-logs", mount_path="/data/logs"),
        ]

        # TODO
        environment_variables = [
            V1EnvVar(name="DEPLOYMENT", value=environment),
            V1EnvVar(name="WEB_CONCURRENCY", value="5"),
            V1EnvVar(name="CLIENT_CODE", value=hdp.tenant),
            V1EnvVar(name="APP_CONFIG_FILE", value="/config/tenant-config.json"),
            V1EnvVar(name="DATABASE_DB", value=ProductName.lower()),
            V1EnvVar(name="DATABASE_HOST", value=get_settings().postgres.host),
            V1EnvVar(name="DATABASE_PASSWORD", value=postgres_password),
            V1EnvVar(name="DATABASE_USER", value=f"{ProductName.lower()}_{hdp.tenant}"),
            V1EnvVar(name="DATABASE_PORT", value=str(get_settings().postgres.port)),
            V1EnvVar(name="DATABASE_DIALECT", value="postgresql"),
            V1EnvVar(name="REDIS_HOST", value=f"cache-new.{hdp.tenant}.svc.cluster.local"),
            V1EnvVar(name="REDIS_PORT", value="6379"),
            V1EnvVar(name="REDIS_PASSWORD", value=redis_password),
            V1EnvVar(name="FLASK_APP", value="superset"),
            V1EnvVar(name="SUPERSET_ENV", value="production"),
            V1EnvVar(name="SUPERSET_SECRET_KEY", value="P90d6HNEeXL2hAU0ciYO9pBZx52jFNKrZsMoNXj8Mo2NlBsAJZTngEzD"),
            V1EnvVar(name="SUPERSET_PORT", value="8088"),
            V1EnvVar(name="MAPBOX_API_KEY", value=""),
            V1EnvVar(name="SUPERSET_URL", value=f"https://{hdp.tenant}.hdp.314ecorp.tech/hdpsuperset"),
            V1EnvVar(name="KEYCLOAK_SUPERSET_PREFIX", value="_hdpdashboard_"),
        ]

        # Volumes
        volumes = [
            V1Volume(
                name="tenant-volume",
                config_map=V1ConfigMapVolumeSource(
                    name="hdp-tenant-config",
                    items=[V1KeyToPath(key="tenant-config.json", path="tenant-config.json")],
                ),
            ),
            V1Volume(
                name="hdp-logs", persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(claim_name="hdp-volume")
            ),
        ]

        # server pod

        superset_password = generate_password(20)
        OnePasswordUtil(
            tenant=f"HDP_{hdp.tenant}",
            server_item="application-config",
            vault=OnePasswordVault,
        ).create_or_replace("superset_password", superset_password)

        StatefulSetPodCreation(
            tenant=hdp.tenant,
            name="hdp",
            docker_image=docker_image,
            request_resource={"cpu": hdp.serverSpec.request_cpu, "memory": hdp.serverSpec.request_memory},
            limit_resource={"cpu": hdp.serverSpec.limit_cpu, "memory": hdp.serverSpec.limit_memory},
            container_ports=[8000],
            volume_mounts=volume_mounts,
            volumes=volumes,
            container_envs=environment_variables,
            init_containers=[
                V1Container(
                    name="hdp-init",
                    image=docker_image,
                    command=["sh", "-c"],
                    args=[
                        f"export FLASK_APP=superset && "
                        f"superset db upgrade && "
                        f"superset fab create-admin --username 'admin' --firstname 'hdp' --lastname 'admin' "
                        f"--email 'superset@314ecorp.com' --password '{superset_password}' && "
                        f"superset init"
                    ],
                )
            ],
        ).put()


class KestraStatefulSetPodCreationActivity(Activity):
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
    @activity.defn(name="KestraStatefulSetPodCreationActivity")
    async def defn(hdp: HDPSpec) -> None:
        """
        Callable for the activity
        """
        # Create k8s stateful set
        from kubernetes.client.models import (
            V1VolumeMount,
            V1Volume,
            V1ConfigMapVolumeSource,
            V1EnvVar,
            V1KeyToPath,
            V1PersistentVolumeClaimVolumeSource,
        )
        from app.cli.activities.statefulSetPodCreation import StatefulSetPodCreation
        from app.core.settings import get_settings, AppSettings
        from app.onepasswordutil import OnePasswordUtil
        from app.common import generate_password

        config: AppSettings = get_settings()

        docker_image = "kestra/kestra:latest-full"

        volume_mounts = [
            V1VolumeMount(name="kestra-volume", mount_path="/config/kestra-config.yml", sub_path="kestra-config.yml"),
            V1VolumeMount(name="kestra-storage", mount_path="/app/storage"),
            V1VolumeMount(name="kestra-tmp", mount_path="/tmp/kestra-wd/tmp"),  # noqa: S108  #nosec
        ]

        volumes = [
            V1Volume(
                name="kestra-volume",
                config_map=V1ConfigMapVolumeSource(
                    name="kestra-config",
                    items=[V1KeyToPath(key="kestra-config.yml", path="kestra-config.yml")],
                ),
            ),
            V1Volume(
                name="kestra-storage",
                persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(claim_name="hdp-volume"),
            ),
            V1Volume(
                name="kestra-tmp", persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(claim_name="hdp-volume")
            ),
        ]

        kestra_password = generate_password(20)

        environment_variables = [
            V1EnvVar(name="KESTRA_CLIENTID", value="hdp"),
            V1EnvVar(name="KESTRA_CLIENTSECRET", value="hdp"),
            V1EnvVar(name="KESTRA_PASSWORD", value=kestra_password),
            V1EnvVar(name="KESTRA_USERNAME", value=config.hdp.kestra_username),
            V1EnvVar(name="KESTRA_CONFIGURATION", value="/config/kestra-config.yml"),
        ]

        OnePasswordUtil(
            tenant=f"hdp_{hdp.tenant}",
            server_item="application-config",
            vault="hdp",
        ).create_or_replace("kestra_password", kestra_password)

        StatefulSetPodCreation(
            tenant=hdp.tenant,
            name="kestra",
            docker_image=docker_image,
            request_resource={"cpu": hdp.serverSpec.request_cpu, "memory": hdp.serverSpec.request_memory},
            limit_resource={"cpu": hdp.serverSpec.limit_cpu, "memory": hdp.serverSpec.limit_memory},
            container_ports=[8080, 8081],
            volume_mounts=volume_mounts,
            volumes=volumes,
            container_envs=environment_variables,
            container_command=["/bin/bash", "-c"],
            container_args=[
                "JAVA_OPTS=-Dmicronaut.server.context-path=/etl"
                " /app/kestra server standalone --port 18080 --worker-thread=128"
            ],
        ).put()


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
        from app.cli.temporal.hdp.hdp import ProductName
        from app.models.tenant import TenantStatusEnum

        status = TenantStatusEnum(activity_input.status)

        await update_tenant_status(
            tenant_name=activity_input.tenant_name,
            product=ProductName,
            status=status,
            error_message=activity_input.error_msg,
        )


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
    async def defn(hdp: HDPSpec) -> None:
        """
        Callable for the activity
        """
        # Send mail to customer
        from app.cli.activities.mail import send_before_provisioning_mail
        from app.core.settings import get_settings

        hdp_config = get_settings().hdp

        await send_before_provisioning_mail(
            user_details={"firstName": hdp.firstName, "lastName": hdp.lastName, "email": hdp.email},
            product=ProductName,
            from_name=hdp_config.sender_name,
            email_from=hdp_config.sender_email,
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
    async def defn(hdp: HDPSpec) -> None:
        """
        Callable for the activity
        """
        # Send mail to customer

        from app.cli.activities.mail import send_provisioning_mail
        from app.core.settings import get_settings

        hdp_config = get_settings().hdp

        await send_provisioning_mail(
            realm_name=hdp.tenant,
            tenant=hdp.tenant,
            user_details={"firstName": hdp.firstName, "lastName": hdp.lastName, "email": hdp.email},
            domain_name=hdp_config.domain_name,
            product=ProductName,
            from_name=hdp_config.sender_name,
            email_from=hdp_config.sender_email,
        )
