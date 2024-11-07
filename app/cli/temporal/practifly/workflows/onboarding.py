from collections.abc import Callable
from temporalio import workflow
import pydash
import orjson
from app.cli.temporal.practifly import TemplatePath
from app.cli.temporal.activities.updateTenantStatus import TenantStatus, UpdateTenantStatusActivity
from app.cli.temporal.activities.temporalNamespace import TemporalNamespaceActivity, TemporalNamespaceActivityModel
from app.cli.temporal.activities.pvcSetup import PVCSetupActivity, PVCSetupActivityModel
from app.cli.temporal.activities.postgresSetup import (
    KeycloakUserMappingActivity,
    KeycloakUserMappingActivityModel,
    PostgresDatabaseCreationActivity,
    PostgresUserCreationActivity,
    PostgresDatabaseCreationActivityModel,
    PostgresUserCreationActivityModel,
    PostgresGrantAccessToUserActivity,
    PostgresGrantAccessToUserActivityModel,
    PostgresSupavisorPollUserActivity,
    PostgresSupavisorPollUserActivityModel,
    PostgresSchemaCreationActivity,
    PostgresSchemaCreationActivityModel,
)
from app.cli.temporal.activities.keycloakSetup import (
    KeycloakClientSetupActivity,
    KeycloakClientSetupActivityModel,
    KeycloakCreateClientRolesActivity,
    KeycloakCreateClientRolesActivityModel,
    KeycloakCreateInternalUsersActivity,
    KeycloakCreateInternalUsersActivityModel,
    KeycloakCreateTenantCustomerAdminUserActivity,
    KeycloakCreateTenantCustomerAdminUserActivityModel,
    KeycloakRealmSetupActivity,
    KeycloakRealmSetupActivityModel,
)
from app.cli.temporal.core.base import Workflow
from app.cli.temporal.practifly.models.practiflySpec import PractiflySpec
from app.cli.temporal.activities.k8sSecret import K8sSecretCreationActivity, K8sSecretCreationActivityModel
from app.cli.temporal.activities.k8sService import KubernetesServiceActivity, KubernetesServiceActivityModel
from app.cli.temporal.activities.k8sconfigMap import K8sConfigMapCreationActivity, K8sConfigMapCreationActivityModel
from app.cli.temporal.activities.vmPodScrapper import VMPodScrapperActivity, VMPodScrapperActivityModel

from app.cli.temporal.activities.redis import RedisSetupActivity, RedisSetupActivityModel
from app.cli.temporal.activities.k8sIstioVirtualService import (
    KubernetesIstioVirtualServiceActivity,
    KubernetesIstioVirtualServiceActivityModel,
)
with workflow.unsafe.imports_passed_through():
    from app.common import generate_password
    from app.core.settings import AppSettings, PractiflySettings, get_settings
    from app.onepasswordutil import OnePasswordUtil
    from app.template_env import get_env


ProductName = "practifly"
OnePasswordVaultName = "practifly"


@workflow.defn(name="PractiflyOnboardingWorkflow", sandboxed=False)
class PractiflyOnboardingWorkflow(Workflow):
    """
    Practifly Onboarding Workflow
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
            UpdateTenantStatusActivity.defn,
            PostgresDatabaseCreationActivity.defn,
            PostgresUserCreationActivity.defn,
            PostgresSupavisorPollUserActivity.defn,
            PostgresSchemaCreationActivity.defn,
            PostgresGrantAccessToUserActivity.defn,
            KeycloakUserMappingActivity.defn,
            KeycloakRealmSetupActivity.defn,
            KeycloakClientSetupActivity.defn,
            KeycloakCreateClientRolesActivity.defn,
            KeycloakCreateTenantCustomerAdminUserActivity.defn,
            KeycloakCreateInternalUsersActivity.defn,
            VMPodScrapperActivity.defn,
            PVCSetupActivity.defn,
            TemporalNamespaceActivity.defn,
            K8sSecretCreationActivity.defn,
            KubernetesServiceActivity.defn,
            KubernetesIstioVirtualServiceActivity.defn,
            RedisSetupActivity.defn,
            K8sConfigMapCreationActivity.defn,
        ]

    @workflow.run
    async def run(self: "Workflow", practifly: PractiflySpec) -> None:
        """
        Run the workflow
        """
        config: AppSettings = get_settings()
        practifly_config: PractiflySettings = config.practifly

        tenant = pydash.get(practifly, "tenant")
        first_name = pydash.get(practifly, "firstName")
        last_name = pydash.get(practifly, "lastName")
        email = pydash.get(practifly, "email")

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

        postgres_schema_name = tenant
        postgres_database_name = ProductName
        postgres_username = f"{ProductName}_{tenant}"
        postgres_password = generate_password(length=20)
        template_env = get_env(template_path=TemplatePath)
        image_tag = "production" if config.env == "production" else "sprint"
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
        
        OnePasswordUtil(
                tenant=f"{ProductName}_{tenant}",
                server_item="application-config",
            vault=OnePasswordVaultName,
        ).create_or_replace("pg_password", postgres_password)
        
        # temporal namespace creation
        await workflow.execute_activity(
            activity=TemporalNamespaceActivity.defn,
            arg=TemporalNamespaceActivityModel(
                namespace=f"{ProductName}_{tenant}",
            ),
            retry_policy=TemporalNamespaceActivity.get_retry_policy(),
            start_to_close_timeout=TemporalNamespaceActivity.get_timeout(),
        )

        # create postgres database
        await workflow.execute_activity(
            activity=PostgresDatabaseCreationActivity.defn,
            arg=PostgresDatabaseCreationActivityModel(
                database_name=postgres_database_name,
            ),
            retry_policy=PostgresDatabaseCreationActivity.get_retry_policy(),
            start_to_close_timeout=PostgresDatabaseCreationActivity.get_timeout(),
        )

        # create postgres user for practifly
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

        await workflow.execute_activity(
            activity=PostgresSupavisorPollUserActivity.defn,
            arg=PostgresSupavisorPollUserActivityModel(
                username=postgres_username,
                database_name=postgres_database_name,
                db_password=postgres_password,
                template_path=TemplatePath,
            ),
            retry_policy=PostgresSupavisorPollUserActivity.get_retry_policy(),
            start_to_close_timeout=PostgresSupavisorPollUserActivity.get_timeout(),
        )

        await workflow.execute_activity(
            activity=PostgresSchemaCreationActivity.defn,
            arg=PostgresSchemaCreationActivityModel(
                schema_name=postgres_schema_name,
                username=postgres_username,
                database_name=postgres_database_name,
            ),
            retry_policy=PostgresSchemaCreationActivity.get_retry_policy(),
            start_to_close_timeout=PostgresSchemaCreationActivity.get_timeout(),
        )

        await workflow.execute_activity(
            activity=PostgresGrantAccessToUserActivity.defn,
            arg=PostgresGrantAccessToUserActivityModel(
                schema_name=postgres_schema_name,
                username=postgres_username,
                database_name=postgres_database_name,
            ),
            retry_policy=PostgresGrantAccessToUserActivity.get_retry_policy(),
            start_to_close_timeout=PostgresGrantAccessToUserActivity.get_timeout(),
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
        
        # kubernetes service
        await workflow.execute_activity(
            activity=KubernetesServiceActivity.defn,
            arg=KubernetesServiceActivityModel(
                namespace=tenant,
                service_name="jeeves",
                port=8000,
            ),
            retry_policy=KubernetesServiceActivity.get_retry_policy(),
            start_to_close_timeout=KubernetesServiceActivity.get_timeout(),
        )
        
        # kubernetes virtual service
        await workflow.execute_activity(
            activity=KubernetesIstioVirtualServiceActivity.defn,
            arg=KubernetesIstioVirtualServiceActivityModel(
                namespace=tenant,
                host=f"{tenant}.api.{practifly_config.domain_name}",
                service_name="jeeves-vs",
                payload=http_list,
            ),
            retry_policy=KubernetesIstioVirtualServiceActivity.get_retry_policy(),
            start_to_close_timeout=KubernetesIstioVirtualServiceActivity.get_timeout(),
        )
        
        # setup redis
        redis_tenant_password = generate_password(length=20)
        OnePasswordUtil(
            tenant=f"{ProductName}_{tenant}",
            server_item="application-config",
            vault=OnePasswordVaultName,
        ).create_or_replace("redis_password", redis_tenant_password)

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
        
        for config_map in [
                {"name": "practifly-tenant-config", "key": "tenant-config.json"},
                {"name": "practifly-rclone-config", "key": "rclone.conf"},
                {"name": "practifly-cli-vector-config", "key": "vector-config.toml"},
                {"name": "practifly-statestore-config", "key": "statestore.yaml"},
            ]:
                await workflow.execute_activity(
                    activity=K8sConfigMapCreationActivity.defn,
                    arg=K8sConfigMapCreationActivityModel(
                        namespace=tenant,
                        name=config_map["name"],
                        template_file_name=config_map["key"],
                        bucket_name="practifly-config",
                        template_payload={"tenant": tenant},
                    ),
                    retry_policy=K8sConfigMapCreationActivity.get_retry_policy(),
                    start_to_close_timeout=K8sConfigMapCreationActivity.get_timeout(),
            )
            
        await workflow.execute_activity(
            activity=KeycloakUserMappingActivity.defn,
            arg=KeycloakUserMappingActivityModel(
                username=postgres_username,
                database_name=postgres_database_name,
            ),
            retry_policy=KeycloakUserMappingActivity.get_retry_policy(),
            start_to_close_timeout=KeycloakUserMappingActivity.get_timeout(),
        )
        
        # keycloak realm setup
        realm_name = tenant
        await workflow.execute_activity(
            activity=KeycloakRealmSetupActivity.defn,
            arg=KeycloakRealmSetupActivityModel(
                tenant=tenant,
                domain=practifly_config.domain_name,
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
                domain=practifly_config.domain_name,
                template_path=TemplatePath,
                template_name="keycloak_practifly_client.json",
            ),
            retry_policy=KeycloakClientSetupActivity.get_retry_policy(),
            start_to_close_timeout=KeycloakClientSetupActivity.get_timeout(),
        )

        roles = [
            ## TODO: add roles here
        ]
        
        # keycloak client roles setup
        await workflow.execute_activity(
            activity=KeycloakCreateClientRolesActivity.defn,
            arg=KeycloakCreateClientRolesActivityModel(
                client_name=ProductName,
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
                client_name=ProductName,
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

        # keycloak internal users setup
        await workflow.execute_activity(
            activity=KeycloakCreateInternalUsersActivity.defn,
            arg=KeycloakCreateInternalUsersActivityModel(
                realm_name=realm_name,
                client_name=ProductName,
                template_path=TemplatePath,
                template_name="keycloak_tenant_internal_user.json",
                users=orjson.loads(open(f"{TemplatePath}/{config.env}_internal_users.json").read()),
            ),
            retry_policy=KeycloakCreateInternalUsersActivity.get_retry_policy(),
            start_to_close_timeout=KeycloakCreateInternalUsersActivity.get_timeout(),
        )
        
        # vm pod scraper
        await workflow.execute_activity(
            activity=VMPodScrapperActivity.defn,
            arg=VMPodScrapperActivityModel(
                namespace=tenant,
                name="practifly-metrics",
                app=ProductName,
                path="/metrics/",
                interval="15s",
            ),
            retry_policy=VMPodScrapperActivity.get_retry_policy(),
            start_to_close_timeout=VMPodScrapperActivity.get_timeout(),
        )
        
        # pvc setup
        await workflow.execute_activity(
            activity=PVCSetupActivity.defn,
            arg=PVCSetupActivityModel(
                tenant=tenant,
                pvc_name="practifly-data",
            ),
            retry_policy=PVCSetupActivity.get_retry_policy(),
            start_to_close_timeout=PVCSetupActivity.get_timeout(),
        )

    @workflow.signal
    async def approve(self: "Workflow") -> None:
        """
        Approve the workflow
        """
        self.approved = True

    @workflow.signal
    async def deny(self: "Workflow") -> None:
        """
        Deny the workflow
        """
        self.deny = True
