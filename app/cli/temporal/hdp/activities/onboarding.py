import dataclasses
from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.hdp.models.hdpSpec import HDPSpec
from app.cli.temporal.core.base import Activity

ProductName = "hdp"
OnePasswordVault = "HDP"


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
        from app.cli.activities.postgresSetup import setup_postgres
        from app.cli.temporal.hdp import TemplatePath
        from app.core.settings import get_settings

        database_name = "HDP"
        schema_name = hdp.tenant
        vault_name = "hdp"

        await setup_postgres(
            tenant=hdp.tenant,
            product_name=ProductName,
            schema_name=schema_name,
            database_name=database_name,
            vault_name=vault_name,
            template_path=TemplatePath,
            config=get_settings().hdp,
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
        from app.cli.activities.configMapSetup import ConfigMapClass

        tenant_config: dict[str, str] = {"name": "hdp-tenant-config", "key": "tenant-config.json"}

        bucket_name = "hdp-config"

        ConfigMapClass(tenant=hdp.tenant, config_map=tenant_config, bucket_name=bucket_name).put()


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

        await RedisSetup(tenant=hdp.tenant, product=ProductName, vault_name="HDP").put()


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

        Service(tenant=hdp.tenant, product=ProductName).put()

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
        from kubernetes.client.models import V1VolumeMount, V1Volume, V1EnvVar, V1ConfigMapVolumeSource, V1KeyToPath

        from app.cli.activities.statefulSetPodCreation import StatefulSetPodCreation
        from app.onepasswordutil import OnePasswordUtil
        from app.core.settings import get_settings

        environment = get_settings().env
        image_tag = "production" if environment == "production" else "sprint"
        docker_image = f"registry.314ecorp.tech/hdp-api:{image_tag}"

        volume_mounts = [
            V1VolumeMount(
                name="tenant-volume",
                mount_path="/config/tenant-config.json",
                sub_path="tenant-config.json",
            ),
        ]

        # TODO
        environment_variables = [
            V1EnvVar(name="DEPLOYMENT", value=environment),
            V1EnvVar(name="WEB_CONCURRENCY", value="5"),
            V1EnvVar(name="CLIENT_CODE", value=hdp.tenant),
            V1EnvVar(name="APP_CONFIG_FILE", value="/config/tenant-config.json"),

            V1EnvVar(name="EXTRACTOR_ENABLED", value="FALSE"),
            V1EnvVar(name="TIKA_SERVER_ENDPOINT", value=get_settings().jeeves.tika_server_endpoint),
            V1EnvVar(name="DYNAMIC_URL_HASH_KEY", value=dynamic_url_hash_key),
            V1EnvVar(name="DYNAMIC_URL_ENABLED", value="True"),
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
        ]

        # server pod
        StatefulSetPodCreation(
            tenant=hdp.tenant,
            name="hdp",
            docker_image=docker_image,
            request_resource={"cpu": hdp.serverSpec.request_cpu, "memory": hdp.serverSpec.request_memory},
            limit_resource={"cpu": hdp.serverSpec.limit_cpu, "memory": hdp.serverSpec.limit_memory},
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

        await send_before_provisioning_mail(
            user_details={"firstName": hdp.firstName, "lastName": hdp.lastName, "email": hdp.email},
            product=ProductName,
            from_name="HDP Support",
            email_from="support@okhdp.com",
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

        await send_provisioning_mail(
            realm_name=hdp.tenant,
            tenant=hdp.tenant,
            user_details={"firstName": hdp.firstName, "lastName": hdp.lastName, "email": hdp.email},
            domain_name=get_settings().hdp.domain_name,
            product=ProductName,
            from_name="HDP Support",
            email_from="support@okhdp.com",
        )
