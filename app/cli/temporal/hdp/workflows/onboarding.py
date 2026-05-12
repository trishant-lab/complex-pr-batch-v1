from collections.abc import Callable

import pydash
from temporalio import workflow

from app.cli.activity_util import run_activity
from app.cli.temporal.activities.dns_setup import DnsSetupActivity, DnsSetupActivityModel
from app.cli.temporal.activities.k8s_config_map import K8sConfigMapCreationActivity, K8sConfigMapCreationActivityModel
from app.cli.temporal.activities.k8s_istio_virtual_service import (
    KubernetesIstioVirtualServiceActivity,
    KubernetesIstioVirtualServiceActivityModel,
)
from app.cli.temporal.activities.k8s_namespace import K8sNamespaceCreationActivity, K8sNamespaceCreationActivityModel
from app.cli.temporal.activities.k8s_secret import K8sSecretCreationActivity, K8sSecretCreationActivityModel
from app.cli.temporal.activities.k8s_service import KubernetesServiceActivity, KubernetesServiceActivityModel
from app.cli.temporal.activities.keycloak_setup import (
    KeycloakClientSetupActivity,
    KeycloakClientSetupActivityModel,
    KeycloakCreateClientRolesActivity,
    KeycloakCreateClientRolesActivityModel,
    KeycloakCreateTenantCustomerAdminUserActivity,
    KeycloakCreateTenantCustomerAdminUserActivityModel,
    KeycloakRealmSetupActivity,
    KeycloakRealmSetupActivityModel,
)
from app.cli.temporal.activities.one_password import (
    OnePasswordCreateOrUpdateActivity,
    OnePasswordCreateOrUpdateActivityModel,
)
from app.cli.temporal.activities.postgres_setup import (
    PostgresDatabaseCreationActivity,
    PostgresDatabaseCreationActivityModel,
    PostgresGrantAccessToUserActivity,
    PostgresGrantAccessToUserActivityModel,
    PostgresUserCreationActivity,
    PostgresUserCreationActivityModel,
)
from app.cli.temporal.activities.pvc_setup import PVCSetupActivity, PVCSetupActivityModel
from app.cli.temporal.activities.redis import CACHE_HOST, RedisSetupActivity, RedisSetupActivityModel
from app.cli.temporal.activities.send_mail import (
    SendAfterProvisioningMailActivity,
    SendAfterProvisioningMailActivityModel,
    SendBeforeProvisioningMailActivity,
    SendBeforeProvisioningMailActivityModel,
)
from app.cli.temporal.activities.stateful_set_pod_creation import (
    KubernetesStatefulSetActivity,
    KubernetesStatefulSetActivityModel,
)
from app.cli.temporal.activities.ui_setup import UiSetupActivity, UiSetupActivityModel
from app.cli.temporal.activities.update_tenant_status import TenantCliStatus, UpdateTenantStatusActivity
from app.cli.temporal.core.base import Workflow
from app.cli.temporal.hdp import TemplatePath
from app.cli.temporal.hdp.models.hdp_spec import HDPSpec
from app.common import generate_password
from app.core.ijson import ijson_loads
from app.core.settings import AppSettings, HDPSettings, get_settings
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum
from app.template_env import get_env

ProductName = "hdp"
OnePasswordVaultName = "hdp"


@workflow.defn(name="HDPOnboardingWorkflow")
class HDPOnboardingWorkflow(Workflow):
    """
    Hdp Onboarding Workflow
    """

    def __init__(self: "Workflow") -> None:
        self.approved: bool = False
        self.denied: bool = False

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
            OnePasswordCreateOrUpdateActivity.defn,
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
                await run_activity(
                    activity=SendBeforeProvisioningMailActivity,
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
                )

            # Wait for approval or denial
            await workflow.wait_condition(lambda: self.approved or self.denied)

            # Update tenant status if request is declined
            if self.denied:
                await run_activity(
                    activity=UpdateTenantStatusActivity,
                    arg=TenantCliStatus(
                        tenant_name=tenant,
                        status=TenantStatusEnum.ApprovalDeclined,
                        error_msg="Request Declined",
                        product=ProductEnum.hdp,
                    ),
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

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item="application-config",
                    vault=OnePasswordVaultName,
                    secret_name="hdp_pg_password",
                    secret_value=postgres_password,
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item="application-config",
                    vault=OnePasswordVaultName,
                    secret_name="kestra_pg_password",
                    secret_value=kestra_postgres_password,
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item="application-config",
                    vault=OnePasswordVaultName,
                    secret_name="kestra_password",
                    secret_value=kestra_password,
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item="application-config",
                    vault=OnePasswordVaultName,
                    secret_name="superset_password",
                    secret_value=superset_password,
                ),
            )

            # create postgres database for hdp
            await run_activity(
                activity=PostgresDatabaseCreationActivity,
                arg=PostgresDatabaseCreationActivityModel(
                    database_name=postgres_database_name,
                ),
            )

            # create postgres database for kestra
            await run_activity(
                activity=PostgresDatabaseCreationActivity,
                arg=PostgresDatabaseCreationActivityModel(
                    database_name=kestra_postgres_database_name,
                ),
            )

            # create postgres user for hdp
            await run_activity(
                activity=PostgresUserCreationActivity,
                arg=PostgresUserCreationActivityModel(
                    username=postgres_username,
                    database_name=postgres_database_name,
                    password=postgres_password,
                ),
            )

            # create postgres user for kestra
            await run_activity(
                activity=PostgresUserCreationActivity,
                arg=PostgresUserCreationActivityModel(
                    username=kestra_postgres_username,
                    database_name=kestra_postgres_database_name,
                    password=kestra_postgres_password,
                ),
            )

            await run_activity(
                activity=PostgresGrantAccessToUserActivity,
                arg=PostgresGrantAccessToUserActivityModel(
                    username=postgres_username,
                    database_name=postgres_database_name,
                ),
            )

            await run_activity(
                activity=PostgresGrantAccessToUserActivity,
                arg=PostgresGrantAccessToUserActivityModel(
                    username=kestra_postgres_username,
                    database_name=kestra_postgres_database_name,
                ),
            )

            await run_activity(
                activity=K8sNamespaceCreationActivity,
                arg=K8sNamespaceCreationActivityModel(
                    namespace=tenant,
                ),
            )

            # secret setup for docker registry
            await run_activity(
                activity=K8sSecretCreationActivity,
                arg=K8sSecretCreationActivityModel(
                    namespace=tenant,
                    name="registrycred",
                    type="kubernetes.io/dockerconfigjson",
                    data={
                        ".dockerconfigjson": config.docker_image_pull_secret,
                    },
                ),
            )

            # setup redis
            redis_tenant_password = f"{ProductName}_{tenant}-{generate_password(length=20)}"
            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item="application-config",
                    vault=OnePasswordVaultName,
                    secret_name="redis_password",
                    secret_value=redis_tenant_password,
                ),
            )

            await run_activity(
                activity=RedisSetupActivity,
                arg=RedisSetupActivityModel(
                    namespace=tenant,
                    product=ProductName,
                    redis_tenant_password=redis_tenant_password,
                ),
            )

            tenant_config = "tenant-config.json"
            kestra_config = "kestra-config.yml"
            config_dir = "config"
            # setup tenant configmap
            for config_map in [
                {
                    "name": "hdp-tenant-config",
                    "key": tenant_config,
                    "template_file_name": f"{config.env}-tenant-config.tmpl.json",
                },
                {
                    "name": "kestra-config",
                    "key": kestra_config,
                    "template_file_name": f"{config.env}-kestra-config.tmpl.yml",
                },
            ]:
                await run_activity(
                    activity=K8sConfigMapCreationActivity,
                    arg=K8sConfigMapCreationActivityModel(
                        namespace=tenant,
                        name=config_map["name"],
                        template_file_name=config_map["template_file_name"],
                        destination_file_name=config_map["key"],
                        bucket_name="hdp-config",
                        template_payload={"tenant": tenant},
                    ),
                )

            # dns setup
            await run_activity(
                activity=DnsSetupActivity,
                arg=DnsSetupActivityModel(
                    cname=config.google_dns_cname,
                    fqdn=f"{tenant}.{hdp_config.domain_name}.",
                    zone_name=hdp_config.zone_name,
                ),
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

            await run_activity(
                activity=UiSetupActivity,
                arg=UiSetupActivityModel(
                    src_object_name=src_object_name,
                    dest_dir=dest_dir,
                    bundle_path=bundle_path,
                    bundle_name="bundle.zip",
                ),
            )

            # superset ui setup
            superset_src_object_name = f"{repo_name}/{image_tag}/bundle_superset.zip"
            superset_bundle_path = "bundle/static"
            superset_dest_dir = f"{tenant}.{hdp_config.domain_name}/static"

            await run_activity(
                activity=UiSetupActivity,
                arg=UiSetupActivityModel(
                    src_object_name=superset_src_object_name,
                    dest_dir=superset_dest_dir,
                    bundle_path=superset_bundle_path,
                    bundle_name="bundle_superset.zip",
                ),
            )

            realm_name = tenant
            # keycloak realm setup
            await run_activity(
                activity=KeycloakRealmSetupActivity,
                arg=KeycloakRealmSetupActivityModel(
                    realm_name=realm_name,
                    domain=hdp_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_realm.json",
                ),
            )

            # keycloak client setup
            await run_activity(
                activity=KeycloakClientSetupActivity,
                arg=KeycloakClientSetupActivityModel(
                    tenant=tenant,
                    realm_name=realm_name,
                    domain=hdp_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_hdp_client.json",
                ),
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
            await run_activity(
                activity=KeycloakCreateClientRolesActivity,
                arg=KeycloakCreateClientRolesActivityModel(
                    client_name="hdp",
                    realm_name=realm_name,
                    roles=roles,
                ),
            )

            # keycloak tenant customer admin user setup
            await run_activity(
                activity=KeycloakCreateTenantCustomerAdminUserActivity,
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
            )

            # kubernetes service
            await run_activity(
                activity=KubernetesServiceActivity,
                arg=KubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="hdp",
                    ports={"http": 8000},
                ),
            )

            template_env = get_env(template_path=TemplatePath)

            template = template_env.get_template("istio-rules.json")
            output = template.render(tenant=tenant, image_tag=image_tag, env=config.env)

            http_list = ijson_loads(output)
            if config.env != "production":
                http_list.append(
                    {
                        "name": "redirect",
                        "match": [{"uri": {"exact": "/"}}],
                        "redirect": {"uri": f"/{image_tag}/"},
                    }
                )

            # kubernetes virtual service
            await run_activity(
                activity=KubernetesIstioVirtualServiceActivity,
                arg=KubernetesIstioVirtualServiceActivityModel(
                    namespace=tenant,
                    host=f"{tenant}.{hdp_config.domain_name}",
                    service_name="hdp-vs",
                    payload=http_list,
                ),
            )

            # pvc setup for hdp
            await run_activity(
                activity=PVCSetupActivity,
                arg=PVCSetupActivityModel(
                    tenant=tenant,
                    pvc_name="hdp-volume",
                ),
            )

            # statefulset pod creation for hdp api
            await run_activity(
                activity=KubernetesStatefulSetActivity,
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
                    container_ports={"http": 8000},
                    volume_mounts=[
                        {
                            "name": "tenant-volume",
                            "mount_path": f"/{config_dir}/{tenant_config}",
                            "sub_path": tenant_config,
                        },
                        {"name": "volume-storage", "mount_path": "/data/logs"},
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "hdp-tenant-config",
                            "key": tenant_config,
                            "path": tenant_config,
                        },
                        {"name": "volume-storage", "persistent_volume_claim": "hdp-volume"},
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "WEB_CONCURRENCY", "value": "5"},
                        {"name": "CLIENT_CODE", "value": tenant},
                        {"name": "APP_CONFIG_FILE", "value": f"/{config_dir}/{tenant_config}"},
                        {"name": "SUPERSET_CONFIG_PATH", "value": "/hdpapi/app/superset_config.py"},
                        {"name": "DATABASE_DB", "value": postgres_database_name},
                        {"name": "DATABASE_HOST", "value": get_settings().postgres.host},
                        {"name": "DATABASE_PASSWORD", "value": postgres_password},
                        {"name": "DATABASE_USER", "value": f"{ProductName.lower()}_{tenant}"},
                        {"name": "DATABASE_PORT", "value": str(get_settings().postgres.port)},
                        {"name": "DATABASE_DIALECT", "value": "postgresql"},
                        {"name": "REDIS_HOST", "value": CACHE_HOST},
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
                    init_containers=[
                        {
                            "name": "hdp-init",
                            "image": docker_image,
                            "command": ["sh", "-c"],
                            "args": [
                                f"export FLASK_APP=superset && "
                                f"superset db upgrade && "
                                f"superset fab create-admin --username 'admin' --firstname 'hdp' --lastname 'admin' "
                                f"--email 'superset@314ecorp.com' --password '{superset_password}' && "
                                f"superset init"
                            ],
                        }
                    ],
                ),
            )

            # pvc setup for hdp
            await run_activity(
                activity=PVCSetupActivity,
                arg=PVCSetupActivityModel(
                    tenant=tenant,
                    pvc_name="kestra-volume",
                ),
            )

            # statefulset pod creation for kestra
            await run_activity(
                activity=KubernetesStatefulSetActivity,
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
                    container_ports={"http": 8080, "https": 8081},
                    container_command=["/bin/bash", "-c"],
                    container_args=[
                        "JAVA_OPTS=-Dmicronaut.server.context-path=/etl"
                        " /app/kestra server standalone --port 18080 --worker-thread=128"
                    ],
                    volume_mounts=[
                        {
                            "name": "kestra-volume",
                            "mount_path": f"/{config_dir}/{kestra_config}",
                            "sub_path": kestra_config,
                        },
                        {
                            "name": "volume-storage",
                            "mount_path": "/app/storage",
                        },
                        {
                            "name": "volume-storage",
                            "mount_path": "/tmp/kestra-wd/tmp",  # noqa: S108  #nosec  #NOSONAR
                        },
                    ],
                    volumes=[
                        {
                            "name": "kestra-volume",
                            "config_map_name": "kestra-config",
                            "key": kestra_config,
                            "path": kestra_config,
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
                                    "key": kestra_config,
                                }
                            },
                        },
                    ],
                ),
            )

            # update tenant status
            await run_activity(
                activity=UpdateTenantStatusActivity,
                arg=TenantCliStatus(tenant_name=tenant, status=TenantStatusEnum.Provisioned, product=ProductEnum.hdp),
            )

            # send mail
            await run_activity(
                activity=SendAfterProvisioningMailActivity,
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
            )

            # job to deploy dashboard
            # await run_activity(
            #     activity=JobActivity,
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
            # )

        except Exception as e:
            workflow.logger.error(f"Error in onboarding workflow: {e}")
            await run_activity(
                activity=UpdateTenantStatusActivity,
                arg=TenantCliStatus(
                    tenant_name=tenant,
                    status=TenantStatusEnum.ProvisioningFailed,
                    error_msg=str(e),
                    product=ProductEnum.hdp,
                ),
            )
            raise e

    @workflow.signal
    async def approve(self: "Workflow") -> None:
        """
        Signal to approve the workflow
        """
        self.approved = True

    @workflow.signal
    async def decline(self: "Workflow") -> None:
        """
        Signal to reject the workflow
        """
        self.denied = True
