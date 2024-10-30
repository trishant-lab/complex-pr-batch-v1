from collections.abc import Callable
import orjson
from temporalio import workflow
import pydash

from app.cli.temporal.activities.dnsSetup import DnsSetupActivity, DnsSetupActivityModel
from app.cli.temporal.activities.k8sIstioVirtualService import (
    KubernetesIstioVirtualServiceActivity,
    KubernetesIstioVirtualServiceActivityModel,
)
from app.cli.temporal.activities.k8sSecret import K8sSecretCreationActivity, K8sSecretCreationActivityModel
from app.cli.temporal.activities.k8sService import KubernetesServiceActivity, KubernetesServiceActivityModel
from app.cli.temporal.activities.k8sconfigMap import K8sConfigMapCreationActivity, K8sConfigMapCreationActivityModel
from app.cli.temporal.activities.keycloakSetup import (
    KeycloakClientSetupActivity,
    KeycloakClientSetupActivityModel,
    KeycloakCreateClientRolesActivity,
    KeycloakCreateClientRolesActivityModel,
    KeycloakCreateTenantCustomerAdminUserActivity,
    KeycloakCreateTenantCustomerAdminUserActivityModel,
    KeycloakRealmSetupActivity,
    KeycloakRealmSetupActivityModel,
)
from app.cli.temporal.activities.pvcSetup import PVCSetupActivity, PVCSetupActivityModel
from app.cli.temporal.activities.redis import RedisSetupActivity, RedisSetupActivityModel
from app.cli.temporal.activities.sendMail import (
    SendAfterProvisioningMailActivity,
    SendAfterProvisioningMailActivityModel,
    SendBeforeProvisioningMailActivity,
    SendBeforeProvisioningMailActivityModel,
)
from app.cli.temporal.activities.statefulSetPodCreation import (
    KubernetesStatefulSetActivity,
    KubernetesStatefulSetActivityModel,
)
from app.cli.temporal.activities.uiSetup import UiSetupActivity, UiSetupActivityModel
from app.cli.temporal.activities.updateTenantStatus import TenantStatus, UpdateTenantStatusActivity
from app.cli.temporal.core.base import Workflow

from app.cli.temporal.activities.postgresSetup import (
    PostgresDatabaseCreationActivity,
    PostgresDatabaseCreationActivityModel,
    PostgresUserCreationActivity,
    PostgresGrantAccessToUserActivityModel,
    PostgresGrantAccessToUserActivity,
    PostgresUserCreationActivityModel,
)

from app.cli.temporal.activities.onePassword import OnePasswordActivity, OnePasswordActivityModel

from app.cli.temporal.activities.k8snamespace import K8sNamespaceCreationActivity, K8sNamespaceCreationActivityModel
from app.cli.temporal.hdp import TemplatePath
from app.cli.temporal.hdp.models.hdpSpec import HDPSpec


with workflow.unsafe.imports_passed_through():
    from app.common import generate_password
    from app.core.settings import AppSettings, HDPSettings, get_settings
    from app.template_env import get_env


ProductName = "hdp"
OnePasswordVaultName = "hdp"


@workflow.defn(name="HDPOnboardingWorkflow", sandboxed=False)
class HDPOnboardingWorkflow(Workflow):
    """
    Hdp Onboarding Workflow
    """

    def __init__(self: "Workflow") -> None:
        self.approved: bool = False
        self.deny: bool = False

    @staticmethod
    def get_activities() -> list[type[Callable]]:  # type: ignore
        """
        Return list of activities used in the workflow
        """
        return [
            SendBeforeProvisioningMailActivity.defn,
            SendAfterProvisioningMailActivity.defn,
            UpdateTenantStatusActivity.defn,
            PostgresUserCreationActivity.defn,
            PostgresDatabaseCreationActivity.defn,
            PostgresGrantAccessToUserActivity.defn,
            K8sNamespaceCreationActivity.defn,
            K8sSecretCreationActivity.defn,
            RedisSetupActivity.defn,
            DnsSetupActivity.defn,
            UiSetupActivity.defn,
            KeycloakRealmSetupActivity.defn,
            KeycloakClientSetupActivity.defn,
            KeycloakCreateClientRolesActivity.defn,
            KeycloakCreateTenantCustomerAdminUserActivity.defn,
            KubernetesStatefulSetActivity.defn,
            KubernetesIstioVirtualServiceActivity.defn,
            KubernetesServiceActivity.defn,
            K8sConfigMapCreationActivity.defn,
            PVCSetupActivity.defn,
            OnePasswordActivity.defn,
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", hdp: HDPSpec) -> str:
        """
        Return workflow id
        """
        return f"hdp_onboarding_workflow_{pydash.get(hdp, 'tenant')}"

    @workflow.run
    async def run(self: "Workflow", hdp: HDPSpec) -> None:
        """
        Run the workflow
        """
        config: AppSettings = get_settings()
        hdp_config: HDPSettings = config.hdp

        first_name = pydash.get(hdp, "firstName")
        last_name = pydash.get(hdp, "lastName")
        email = pydash.get(hdp, "email")
        tenant = pydash.get(hdp, "tenant")

        try:
            if not pydash.get(hdp, "emailSent"):
                await workflow.execute_activity(
                    activity=SendBeforeProvisioningMailActivity.defn,
                    arg=SendBeforeProvisioningMailActivityModel(
                        user_details={
                            "firstName": first_name,
                            "lastName": last_name,
                            "email": email,
                        },
                        product=ProductName,
                        from_name=hdp_config.sender_name,
                        email_from=hdp_config.sender_email,
                    ),
                    retry_policy=SendBeforeProvisioningMailActivity.get_retry_policy(),
                    start_to_close_timeout=SendBeforeProvisioningMailActivity.get_timeout(),
                )

            # Wait for approval or denial
            await workflow.wait_condition(lambda: self.approved or self.deny)

            # Update tenant status if request is declined
            if self.deny:
                await workflow.execute_activity(
                    activity=UpdateTenantStatusActivity.defn,
                    arg=TenantStatus(
                        tenant_name=tenant,
                        status="Declined",
                        error_msg="Request Declined",
                    ),
                    start_to_close_timeout=UpdateTenantStatusActivity.get_timeout(),
                    retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
                )

            postgres_database_name = f"hdp_{tenant}"
            kestra_postgres_database_name = f"kestra_{tenant}"
            postgres_username = f"{ProductName}_{tenant}"
            kestra_postgres_username = f"kestra_{tenant}"
            postgres_password = generate_password(length=20)
            kestra_postgres_password = generate_password(length=20)
            image_tag = "production" if config.env == "production" else "sprint"
            docker_image = f"registry.314ecorp.tech/hdp-api:{image_tag}"
            kestra_password = generate_password(20)
            superset_password = generate_password(20)

            await workflow.execute_activity(
                activity=OnePasswordActivity.defn,
                arg=OnePasswordActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item="application-config",
                    vault=OnePasswordVaultName,
                    secret_name="hdp_pg_password",
                    secret_value=postgres_password,
                ),
                retry_policy=OnePasswordActivity.get_retry_policy(),
                start_to_close_timeout=OnePasswordActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=OnePasswordActivity.defn,
                arg=OnePasswordActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item="application-config",
                    vault=OnePasswordVaultName,
                    secret_name="kestra_pg_password",
                    secret_value=kestra_postgres_password,
                ),
                retry_policy=OnePasswordActivity.get_retry_policy(),
                start_to_close_timeout=OnePasswordActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=OnePasswordActivity.defn,
                arg=OnePasswordActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item="application-config",
                    vault=OnePasswordVaultName,
                    secret_name="kestra_password",
                    secret_value=kestra_password,
                ),
                retry_policy=OnePasswordActivity.get_retry_policy(),
                start_to_close_timeout=OnePasswordActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=OnePasswordActivity.defn,
                arg=OnePasswordActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item="application-config",
                    vault=OnePasswordVaultName,
                    secret_name="superset_password",
                    secret_value=superset_password,
                ),
                retry_policy=OnePasswordActivity.get_retry_policy(),
                start_to_close_timeout=OnePasswordActivity.get_timeout(),
            )

            # create postgres database for hdp
            await workflow.execute_activity(
                activity=PostgresDatabaseCreationActivity.defn,
                arg=PostgresDatabaseCreationActivityModel(
                    database_name=postgres_database_name,
                ),
                retry_policy=PostgresDatabaseCreationActivity.get_retry_policy(),
                start_to_close_timeout=PostgresDatabaseCreationActivity.get_timeout(),
            )

            # create postgres database for kestra
            await workflow.execute_activity(
                activity=PostgresDatabaseCreationActivity.defn,
                arg=PostgresDatabaseCreationActivityModel(
                    database_name=kestra_postgres_database_name,
                ),
                retry_policy=PostgresDatabaseCreationActivity.get_retry_policy(),
                start_to_close_timeout=PostgresDatabaseCreationActivity.get_timeout(),
            )

            # create postgres user for hdp
            await workflow.execute_activity(
                activity=PostgresUserCreationActivity.defn,
                arg=PostgresUserCreationActivityModel(
                    username=postgres_username,
                    database_name=postgres_database_name,
                    password=postgres_password,
                ),
                retry_policy=PostgresUserCreationActivity.get_retry_policy(),
                start_to_close_timeout=PostgresUserCreationActivity.get_timeout(),
            )

            # create postgres user for kestra
            await workflow.execute_activity(
                activity=PostgresUserCreationActivity.defn,
                arg=PostgresUserCreationActivityModel(
                    username=kestra_postgres_username,
                    database_name=kestra_postgres_database_name,
                    password=kestra_postgres_password,
                ),
                retry_policy=PostgresUserCreationActivity.get_retry_policy(),
                start_to_close_timeout=PostgresUserCreationActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=PostgresGrantAccessToUserActivity.defn,
                arg=PostgresGrantAccessToUserActivityModel(
                    username=postgres_username,
                    database_name=postgres_database_name,
                ),
                retry_policy=PostgresGrantAccessToUserActivity.get_retry_policy(),
                start_to_close_timeout=PostgresGrantAccessToUserActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=PostgresGrantAccessToUserActivity.defn,
                arg=PostgresGrantAccessToUserActivityModel(
                    username=kestra_postgres_username,
                    database_name=kestra_postgres_database_name,
                ),
                retry_policy=PostgresGrantAccessToUserActivity.get_retry_policy(),
                start_to_close_timeout=PostgresGrantAccessToUserActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=K8sNamespaceCreationActivity.defn,
                arg=K8sNamespaceCreationActivityModel(
                    namespace=tenant,
                ),
                retry_policy=K8sNamespaceCreationActivity.get_retry_policy(),
                start_to_close_timeout=K8sNamespaceCreationActivity.get_timeout(),
            )

            # secret setup for docker registry
            await workflow.execute_activity(
                activity=K8sSecretCreationActivity.defn,
                arg=K8sSecretCreationActivityModel(
                    namespace=tenant,
                    name="registrycred",
                    type="kubernetes.io/dockerconfigjson",
                    data={
                        ".dockerconfigjson": config.docker_image_pull_secret,
                    },
                ),
                retry_policy=K8sSecretCreationActivity.get_retry_policy(),
                start_to_close_timeout=K8sSecretCreationActivity.get_timeout(),
            )

            # secret setup for redis password
            await workflow.execute_activity(
                activity=K8sSecretCreationActivity.defn,
                arg=K8sSecretCreationActivityModel(
                    namespace=tenant,
                    name="cache-secret",
                    string_data={"REDIS_PASSWORD": config.cache_admin_password},
                ),
                retry_policy=K8sSecretCreationActivity.get_retry_policy(),
                start_to_close_timeout=K8sSecretCreationActivity.get_timeout(),
            )

            # setup redis
            redis_tenant_password = generate_password(length=20)
            await workflow.execute_activity(
                activity=OnePasswordActivity.defn,
                arg=OnePasswordActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item="application-config",
                    vault=OnePasswordVaultName,
                    secret_name="redis_password",
                    secret_value=redis_tenant_password,
                ),
                retry_policy=OnePasswordActivity.get_retry_policy(),
                start_to_close_timeout=OnePasswordActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=RedisSetupActivity.defn,
                arg=RedisSetupActivityModel(
                    namespace=tenant,
                    product=ProductName,
                    redis_tenant_password=redis_tenant_password,
                ),
                retry_policy=RedisSetupActivity.get_retry_policy(),
                start_to_close_timeout=RedisSetupActivity.get_timeout(),
            )

            # setup tenant configmap
            for config_map in [
                {"name": "hdp-tenant-config", "key": "tenant-config.json"},
                {"name": "kestra-config", "key": "kestra-config.yml"},
            ]:
                await workflow.execute_activity(
                    activity=K8sConfigMapCreationActivity.defn,
                    arg=K8sConfigMapCreationActivityModel(
                        namespace=tenant,
                        name=config_map["name"],
                        template_file_name=config_map["key"],
                        bucket_name="hdp-config",
                        template_payload={"tenant": tenant},
                    ),
                    retry_policy=K8sConfigMapCreationActivity.get_retry_policy(),
                    start_to_close_timeout=K8sConfigMapCreationActivity.get_timeout(),
                )

            # dns setup
            await workflow.execute_activity(
                activity=DnsSetupActivity.defn,
                arg=DnsSetupActivityModel(
                    cname=config.google_dns_cname,
                    fqdn=f"{tenant}.{hdp_config.domain_name}.",
                    zone_name=hdp_config.zone_name,
                ),
                retry_policy=DnsSetupActivity.get_retry_policy(),
                start_to_close_timeout=DnsSetupActivity.get_timeout(),
            )

            # ui setup
            repo_name = "hdp-ui"
            image_tag = "production" if config.env == "production" else "sprint"

            if config.env == "production":
                dest_dir = f"{tenant}.{hdp_config.domain_name}/"
            else:
                dest_dir = f"{tenant}.{hdp_config.domain_name}/{image_tag}"

            src_object_name = f"{repo_name}/{image_tag}/bundle.zip"

            bundle_path = "bundle/dist"

            await workflow.execute_activity(
                activity=UiSetupActivity.defn,
                arg=UiSetupActivityModel(
                    src_object_name=src_object_name,
                    dest_dir=dest_dir,
                    bundle_path=bundle_path,
                    bundle_name="bundle.zip",
                ),
                retry_policy=UiSetupActivity.get_retry_policy(),
                start_to_close_timeout=UiSetupActivity.get_timeout(),
            )

            # superset ui setup
            superset_src_object_name = f"{repo_name}/{image_tag}/bundle_superset.zip"
            superset_bundle_path = "bundle/static"
            superset_dest_dir = f"{tenant}.{hdp_config.domain_name}/static"

            await workflow.execute_activity(
                activity=UiSetupActivity.defn,
                arg=UiSetupActivityModel(
                    src_object_name=superset_src_object_name,
                    dest_dir=superset_dest_dir,
                    bundle_path=superset_bundle_path,
                    bundle_name="bundle_superset.zip",
                ),
                retry_policy=UiSetupActivity.get_retry_policy(),
                start_to_close_timeout=UiSetupActivity.get_timeout(),
            )

            realm_name = tenant
            # keycloak realm setup
            await workflow.execute_activity(
                activity=KeycloakRealmSetupActivity.defn,
                arg=KeycloakRealmSetupActivityModel(
                    tenant=tenant,
                    domain=hdp_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_realm.json",
                ),
                retry_policy=KeycloakRealmSetupActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakRealmSetupActivity.get_timeout(),
            )

            # keycloak client setup
            await workflow.execute_activity(
                activity=KeycloakClientSetupActivity.defn,
                arg=KeycloakClientSetupActivityModel(
                    tenant=tenant,
                    realm_name=realm_name,
                    domain=hdp_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_hdp_client.json",
                ),
                retry_policy=KeycloakClientSetupActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakClientSetupActivity.get_timeout(),
            )

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
            # keycloak client roles setup
            await workflow.execute_activity(
                activity=KeycloakCreateClientRolesActivity.defn,
                arg=KeycloakCreateClientRolesActivityModel(
                    client_name="hdp",
                    realm_name=realm_name,
                    roles=roles,
                ),
                retry_policy=KeycloakCreateClientRolesActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakCreateClientRolesActivity.get_timeout(),
            )

            # keycloak tenant customer admin user setup
            await workflow.execute_activity(
                activity=KeycloakCreateTenantCustomerAdminUserActivity.defn,
                arg=KeycloakCreateTenantCustomerAdminUserActivityModel(
                    realm_name=realm_name,
                    client_name="hdp",
                    username=email,
                    email=email,
                    firstname=first_name,
                    lastname=last_name,
                    template_path=TemplatePath,
                    template_name="keycloak_tenant_customer_admin.json",
                ),
                retry_policy=KeycloakCreateTenantCustomerAdminUserActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakCreateTenantCustomerAdminUserActivity.get_timeout(),
            )

            # kubernetes service
            await workflow.execute_activity(
                activity=KubernetesServiceActivity.defn,
                arg=KubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="hdp",
                    port=8000,
                ),
                retry_policy=KubernetesServiceActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesServiceActivity.get_timeout(),
            )

            template_env = get_env(template_path=TemplatePath)

            template = template_env.get_template("istio-rules.json")
            output = template.render(tenant=tenant, image_tag=image_tag, env=config.env)

            http_list = orjson.loads(output)
            if config.env != "production":
                http_list.append(
                    {
                        "name": "redirect",
                        "match": [{"uri": {"exact": "/"}}],
                        "redirect": {"uri": f"/{image_tag}/"},
                    }
                )

            # kubernetes virtual service
            await workflow.execute_activity(
                activity=KubernetesIstioVirtualServiceActivity.defn,
                arg=KubernetesIstioVirtualServiceActivityModel(
                    namespace=tenant,
                    host=f"{tenant}.{hdp_config.domain_name}",
                    service_name="hdp-vs",
                    payload=http_list,
                ),
                retry_policy=KubernetesIstioVirtualServiceActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesIstioVirtualServiceActivity.get_timeout(),
            )

            # pvc setup for hdp
            await workflow.execute_activity(
                activity=PVCSetupActivity.defn,
                arg=PVCSetupActivityModel(
                    tenant=tenant,
                    pvc_name="hdp-volume",
                ),
                retry_policy=PVCSetupActivity.get_retry_policy(),
                start_to_close_timeout=PVCSetupActivity.get_timeout(),
            )

            # statefulset pod creation for hdp api
            await workflow.execute_activity(
                activity=KubernetesStatefulSetActivity.defn,
                arg=KubernetesStatefulSetActivityModel(
                    namespace=tenant,
                    name="hdp",
                    docker_image=docker_image,
                    request_resource={
                        "cpu": pydash.get(hdp, "serverSpec.request_cpu"),
                        "memory": pydash.get(hdp, "serverSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(hdp, "serverSpec.limit_cpu"),
                        "memory": pydash.get(hdp, "serverSpec.limit_memory"),
                    },
                    container_ports=[8000],
                    volume_mounts=[
                        {
                            "name": "tenant-volume",
                            "mount_path": "/config/tenant-config.json",
                            "sub_path": "tenant-config.json",
                        },
                        {"name": "volume-storage", "mount_path": "/data/logs"},
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "hdp-tenant-config",
                            "key": "tenant-config.json",
                            "path": "tenant-config.json",
                        },
                        {"name": "volume-storage", "persistent_volume_claim": "hdp-volume"},
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "WEB_CONCURRENCY", "value": "5"},
                        {"name": "CLIENT_CODE", "value": tenant},
                        {"name": "APP_CONFIG_FILE", "value": "/config/tenant-config.json"},
                        {"name": "DATABASE_DB", "value": postgres_database_name},
                        {"name": "DATABASE_HOST", "value": get_settings().postgres.host},
                        {"name": "DATABASE_PASSWORD", "value": postgres_password},
                        {"name": "DATABASE_USER", "value": f"{ProductName.lower()}_{tenant}"},
                        {"name": "DATABASE_PORT", "value": str(get_settings().postgres.port)},
                        {"name": "DATABASE_DIALECT", "value": "postgresql"},
                        {"name": "REDIS_HOST", "value": f"cache-new.{tenant}.svc.cluster.local"},
                        {"name": "REDIS_PORT", "value": "6379"},
                        {"name": "REDIS_PASSWORD", "value": redis_tenant_password},
                        {"name": "FLASK_APP", "value": "superset"},
                        {"name": "SUPERSET_ENV", "value": "production"},
                        {
                            "name": "SUPERSET_SECRET_KEY",
                            "value": "P90d6HNEeXL2hAU0ciYO9pBZx52jFNKrZsMoNXj8Mo2NlBsAJZTngEzD",
                        },
                        {"name": "SUPERSET_PORT", "value": "8088"},
                        {"name": "MAPBOX_API_KEY", "value": ""},
                        {"name": "SUPERSET_URL", "value": f"https://{tenant}.hdp.314ecorp.tech/hdpsuperset"},
                        {"name": "KEYCLOAK_SUPERSET_PREFIX", "value": "_hdpdashboard_"},
                    ],
                    # init_containers=[{
                    #     "name": "hdp-init",
                    #     "image": docker_image,
                    #     "command": ["sh", "-c"],
                    #     "args": [
                    #         f"export FLASK_APP=superset && "
                    #         f"superset db upgrade && "
                    #         f"superset fab create-admin --username 'admin' --firstname 'hdp' --lastname 'admin' "
                    #         f"--email 'superset@314ecorp.com' --password '{superset_password}' && "
                    #         f"superset init"
                    #     ],
                    # }]
                ),
                retry_policy=KubernetesStatefulSetActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesStatefulSetActivity.get_timeout(),
            )

            # pvc setup for hdp
            await workflow.execute_activity(
                activity=PVCSetupActivity.defn,
                arg=PVCSetupActivityModel(
                    tenant=tenant,
                    pvc_name="kestra-volume",
                ),
                retry_policy=PVCSetupActivity.get_retry_policy(),
                start_to_close_timeout=PVCSetupActivity.get_timeout(),
            )

            # statefulset pod creation for kestra
            await workflow.execute_activity(
                activity=KubernetesStatefulSetActivity.defn,
                arg=KubernetesStatefulSetActivityModel(
                    namespace=tenant,
                    name="kestra",
                    docker_image="kestra/kestra:latest-full",
                    request_resource={
                        "cpu": pydash.get(hdp, "kestraSpec.request_cpu"),
                        "memory": pydash.get(hdp, "kestraSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(hdp, "kestraSpec.limit_cpu"),
                        "memory": pydash.get(hdp, "kestraSpec.limit_memory"),
                    },
                    container_ports=[8080, 8081],
                    container_command=["/bin/bash", "-c"],
                    container_args=[
                        "JAVA_OPTS=-Dmicronaut.server.context-path=/etl"
                        " /app/kestra server standalone --port 18080 --worker-thread=128"
                    ],
                    volume_mounts=[
                        {
                            "name": "kestra-volume",
                            "mount_path": "/config/kestra-config.yml",
                            "sub_path": "kestra-config.yml",
                        },
                        {
                            "name": "volume-storage",
                            "mount_path": "/app/storage",
                        },
                        {
                            "name": "volume-storage",
                            "mount_path": "/tmp/kestra-wd/tmp",  # noqa: S108  #nosec
                        },
                    ],
                    volumes=[
                        {
                            "name": "kestra-volume",
                            "config_map_name": "kestra-config",
                            "key": "kestra-config.yml",
                            "path": "kestra-config.yml",
                        },
                        {"name": "volume-storage", "persistent_volume_claim": "kestra-volume"},
                    ],
                    container_envs=[
                        {"name": "KESTRA_CLIENTID", "value": "hdp"},
                        {"name": "KESTRA_CLIENTSECRET", "value": "hdp"},
                        {"name": "KESTRA_PASSWORD", "value": kestra_password},
                        {"name": "KESTRA_USERNAME", "value": hdp_config.kestra_username},
                        {
                            "name": "KESTRA_CONFIGURATION",
                            "value_from": {
                                "config_map_key_ref": {
                                    "name": "kestra-config",
                                    "key": "kestra-config.yml",
                                }
                            },
                        },
                    ],
                ),
                retry_policy=KubernetesStatefulSetActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesStatefulSetActivity.get_timeout(),
            )

            # update tenant status
            await workflow.execute_activity(
                activity=UpdateTenantStatusActivity.defn,
                arg=TenantStatus(tenant_name=tenant, status="Completed"),
                retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
                start_to_close_timeout=UpdateTenantStatusActivity.get_timeout(),
            )

            # send mail
            await workflow.execute_activity(
                activity=SendAfterProvisioningMailActivity.defn,
                arg=SendAfterProvisioningMailActivityModel(
                    realm_name=realm_name,
                    tenant=tenant,
                    user_details={
                        "firstName": first_name,
                        "lastName": last_name,
                        "email": email,
                    },
                    domain_name=hdp_config.domain_name,
                    product=ProductName,
                    from_name=hdp_config.sender_name,
                    email_from=hdp_config.sender_email,
                ),
                retry_policy=SendAfterProvisioningMailActivity.get_retry_policy(),
                start_to_close_timeout=SendAfterProvisioningMailActivity.get_timeout(),
            )

            # job to deploy dashboard
            # await workflow.execute_activity(
            #     activity=JobActivity.defn,
            #     arg=JobActivityModel(
            #         namespace=tenant,
            #         job_name="hdp-dashboard-deploy",
            #         docker_image=docker_image,
            #         volumes=[],
            #         volume_mounts=[],
            #         container_envs=[
            #             {"name": "SUPERSET_URL", "value": f"https://{tenant}.hdp.314ecorp.tech/hdpsuperset"},
            #             {"name": "SUPERSET_ADMIN_USERNAME", "value": "admin"},
            #             {"name": "SUPERSET_ADMIN_PASSWORD", "value": superset_password},
            #             {"name": "STARROCKS_HOST", "value": ""},
            #             {"name": "STARROCKS_PORT", "value": ""},
            #             {"name": "STARROCKS_USERNAME", "value": ""},
            #             {"name": "STARROCKS_PASSWORD", "value": ""},
            #         ],
            #         argument="",
            #         job_type="dashboard",
            #         product=ProductName,
            #     ),
            #     retry_policy=JobActivity.get_retry_policy(),
            #     start_to_close_timeout=JobActivity.get_timeout(),
            # )

        except Exception as e:
            workflow.logger.error(f"Error in onboarding workflow: {e}")
            await workflow.execute_activity(
                activity=UpdateTenantStatusActivity.defn,
                arg=TenantStatus(
                    tenant_name=tenant,
                    status="Failed",
                    error_msg=str(e),
                ),
                retry_policy=UpdateTenantStatusActivity.get_retry_policy(),
                start_to_close_timeout=UpdateTenantStatusActivity.get_timeout(),
            )
            raise e

    @workflow.signal
    async def approve(self: "Workflow") -> None:
        """
        Signal to approve the workflow
        """
        self.approved = True

    @workflow.signal
    async def deny(self: "Workflow") -> None:
        """
        Signal to reject the workflow
        """
        self.deny = True
