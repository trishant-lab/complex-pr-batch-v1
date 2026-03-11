from collections.abc import Callable

from temporalio import workflow

from app.cli.activity_util import run_activity
from app.cli.temporal.activities.chatwoot_setup import (
    ChatwootSetupActivity,
    ChatwootSetupActivityModel,
)
from app.cli.temporal.activities.database_migration_job import (
    DatabaseMigrationJobActivity,
    DatabaseMigrationJobActivityModel,
)
from app.cli.temporal.activities.deployment_pod_creation import (
    KubernetesDeploymentUpdateActivity,
    KubernetesDeploymentUpdateActivityModel,
)
from app.cli.temporal.activities.jeeves_fetch_latest_tag import (
    JeevesFetchLatestTagActivity,
)
from app.cli.temporal.activities.jeeves_novu_setup import JeevesNovuSetupActivity, JeevesNovuSetupActivityModel
from app.cli.temporal.activities.k8s_config_map import (
    K8sConfigMapCreationActivity,
    K8sConfigMapCreationActivityModel,
)
from app.cli.temporal.activities.keycloak_setup import (
    KeycloakClientSetupActivity,
    KeycloakClientSetupActivityModel,
    KeycloakCreateClientRolesActivity,
    KeycloakCreateClientRolesActivityModel,
    KeycloakCreateGroupActivity,
    KeycloakCreateGroupActivityModel,
    KeycloakCreateInternalUsersActivity,
    KeycloakCreateInternalUsersActivityModel,
    KeycloakCreateTenantCustomerAdminUserActivity,
    KeycloakCreateTenantCustomerAdminUserActivityModel,
    KeycloakUpdateClientMapperActivity,
    KeycloakUpdateClientMapperActivityModel,
)
from app.cli.temporal.activities.one_password import (
    OnePasswordCreateOrUpdateActivity,
    OnePasswordCreateOrUpdateActivityModel,
    OnePasswordGetActivity,
    OnePasswordGetActivityModel,
)
from app.cli.temporal.activities.postgres_setup import (
    PostgresGrantAccessToUserActivity,
    PostgresGrantAccessToUserActivityModel,
    PostgresGrantAllPrivilegesActivityModel,
    PostgresGrantAllPrivilegesOnFunctionsActivity,
    PostgresGrantAllPrivilegesOnSchemaActivity,
    PostgresGrantAllPrivilegesOnSequencesActivity,
    PostgresGrantAllPrivilegesOnTablesActivity,
    PostgresSchemaCreationActivity,
    PostgresSchemaCreationActivityModel,
)
from app.cli.temporal.activities.redis import (
    RedisSetupActivity,
    RedisSetupActivityModel,
)
from app.cli.temporal.activities.slack_notification_activity import (
    SlackNotificationActivity,
)
from app.cli.temporal.activities.update_space_status import (
    UpdateSpaceStatusActivity,
    SpaceStatusModel,
)
from app.cli.temporal.activities.vespa_job import VespaJobActivity, VespaJobActivityModel
from app.cli.temporal.core.base import Workflow
from app.cli.temporal.jeeves import TemplatePath
from app.cli.temporal.jeeves.models.jeeves_spec import SpaceSpec
from app.common import generate_password
from app.core.settings import AppSettings, JeevesSettings, get_settings
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum

ProductName = "jeeves"
OnePasswordVaultName = "Jeeves"
JeevesSystemUser = "jeeves-systemuser@314ecorp.com"


@workflow.defn(name="JeevesSpaceCreationWorkflow", sandboxed=False)
class JeevesSpaceCreationWorkflow(Workflow):
    """
    Jeeves Space Creation Workflow
    Creates a new space (EHR configuration) for an existing tenant
    """

    def __init__(self: "Workflow") -> None:
        super().__init__()

    @staticmethod
    def get_activities() -> list[type[Callable]]:  # type: ignore
        """
        Return list of activities used in the workflow
        """
        return [
            PostgresSchemaCreationActivity.defn,
            PostgresGrantAccessToUserActivity.defn,
            PostgresGrantAllPrivilegesOnTablesActivity.defn,
            PostgresGrantAllPrivilegesOnSequencesActivity.defn,
            PostgresGrantAllPrivilegesOnFunctionsActivity.defn,
            PostgresGrantAllPrivilegesOnSchemaActivity.defn,
            ChatwootSetupActivity.defn,
            JeevesNovuSetupActivity.defn,
            RedisSetupActivity.defn,
            KeycloakClientSetupActivity.defn,
            KeycloakCreateClientRolesActivity.defn,
            KeycloakCreateTenantCustomerAdminUserActivity.defn,
            KeycloakCreateInternalUsersActivity.defn,
            KeycloakCreateGroupActivity.defn,
            KeycloakUpdateClientMapperActivity.defn,
            VespaJobActivity.defn,
            OnePasswordCreateOrUpdateActivity.defn,
            SlackNotificationActivity.defn,
            K8sConfigMapCreationActivity.defn,
            DatabaseMigrationJobActivity.defn,
            JeevesFetchLatestTagActivity.defn,
            UpdateSpaceStatusActivity.defn,
            OnePasswordGetActivity.defn,
            KubernetesDeploymentUpdateActivity.defn,
        ]

    @staticmethod
    def get_space_config(tenant: str, space: str, space_display_name: str) -> dict[str, str]:
        """
        Return space config based on space
        """
        idp_template_map = {
            "cerner": "keycloak_cerner_ehr_idp_flows.json",
            "epic": "keycloak_epic_ehr_idp_flows.json",
        }

        return {
            "keycloak_client_name": f"{ProductName}-{space}",
            "vespa_index_name": f"jeeves_{tenant}_{space}",
            "space_name": f"{tenant}-{space}",
            "db_schema_name": f"{tenant}-{space}",
            "idp_template": idp_template_map.get(space, "keycloak_idp_and_flows.json"),
            "space_display_name": space_display_name,
        }

    @classmethod
    def get_workflow_id(cls: "Workflow", jeeves: SpaceSpec) -> str:
        """
        Return workflow id
        """
        return f"jeeves_space_creation_workflow_{jeeves.tenant}_{jeeves.ehr}"

    @workflow.run
    async def run(self: "Workflow", jeeves: SpaceSpec) -> None:
        """
        Run the space creation workflow
        """
        config: AppSettings = get_settings()
        jeeves_config: JeevesSettings = config.jeeves
        space_display_name = jeeves.get("spaceDisplayName")
        email = jeeves.get("email", "")
        tenant = jeeves.get("tenant", "")
        space = jeeves.get("space", "")
        first_name = jeeves.get("firstName", "")
        last_name = jeeves.get("lastName", "")
        space_config: dict[str, str] = JeevesSpaceCreationWorkflow.get_space_config(tenant, space, space_display_name)
        space_name = space_config["space_name"]
        product_space_name = f"{ProductName}-{space_name}"
        space_display_name = space_config["space_display_name"]

        try:
            # Postgres Setup
            postgres_schema_name = space_config["db_schema_name"]
            postgres_database_name = ProductName
            postgres_username = f"{ProductName}_{tenant}"
            client_name = space_config["keycloak_client_name"]

            await run_activity(
                activity=PostgresSchemaCreationActivity,
                arg=PostgresSchemaCreationActivityModel(
                    schema_name=postgres_schema_name,
                    username=postgres_username,
                    database_name=postgres_database_name,
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=product_space_name,
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    secret_name="db_schema_name",
                    secret_value=postgres_schema_name,
                ),
            )

            await run_activity(
                activity=PostgresGrantAccessToUserActivity,
                arg=PostgresGrantAccessToUserActivityModel(
                    schema_name=postgres_schema_name,
                    username=postgres_username,
                    database_name=postgres_database_name,
                ),
            )

            await run_activity(
                activity=PostgresGrantAllPrivilegesOnTablesActivity,
                arg=PostgresGrantAllPrivilegesActivityModel(
                    posthog_username=jeeves_config.posthog_username,
                    database_name=postgres_database_name,
                    schema_name=postgres_schema_name,
                ),
            )

            await run_activity(
                activity=PostgresGrantAllPrivilegesOnFunctionsActivity,
                arg=PostgresGrantAllPrivilegesActivityModel(
                    posthog_username=jeeves_config.posthog_username,
                    database_name=postgres_database_name,
                    schema_name=postgres_schema_name,
                ),
            )

            await run_activity(
                activity=PostgresGrantAllPrivilegesOnSequencesActivity,
                arg=PostgresGrantAllPrivilegesActivityModel(
                    posthog_username=jeeves_config.posthog_username,
                    database_name=postgres_database_name,
                    schema_name=postgres_schema_name,
                ),
            )

            await run_activity(
                activity=PostgresGrantAllPrivilegesOnSchemaActivity,
                arg=PostgresGrantAllPrivilegesActivityModel(
                    posthog_username=jeeves_config.posthog_username,
                    database_name=postgres_database_name,
                    schema_name=postgres_schema_name,
                ),
            )

            # Redis Setup (using existing tenant redis)
            redis_tenant_password = f"{product_space_name}_{tenant}-{generate_password(length=20)}"
            await run_activity(
                activity=RedisSetupActivity,
                arg=RedisSetupActivityModel(
                    namespace=tenant,
                    product=product_space_name,
                    redis_tenant_password=redis_tenant_password,
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=product_space_name,
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    secret_name="redis_password",
                    secret_value=redis_tenant_password,
                ),
            )

            # Novu Setup
            await run_activity(
                activity=JeevesNovuSetupActivity,
                arg=JeevesNovuSetupActivityModel(
                    jeeves=jeeves,
                    space_name=product_space_name,
                ),
            )

            # Chatwoot Setup
            await run_activity(
                activity=ChatwootSetupActivity,
                arg=ChatwootSetupActivityModel(
                    tenant_space_name=product_space_name,
                    tenant=tenant,
                    product=ProductName,
                    config=jeeves_config,
                ),
            )

            space_names = await run_activity(
                activity=OnePasswordGetActivity,
                arg=OnePasswordGetActivityModel(
                    tenant=f"{ProductName}-{tenant}",
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    secret_name="space_names",
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}-{tenant}",
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    secret_name="space_names",
                    secret_value=space_names.strip("'\" ").replace('"",""', '","') + '","' + client_name,
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=product_space_name,
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    secret_name="space_display_name",
                    secret_value=space_display_name,
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=product_space_name,
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    secret_name="vespa_index_name",
                    secret_value=space_config["vespa_index_name"],
                ),
            )

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=product_space_name,
                    vault=OnePasswordVaultName,
                    server_item="application-config",
                    secret_name="space_name",
                    secret_value=client_name,
                ),
            )

            # Setup space-specific configmap
            space_config_file = f"{space}.json"
            await run_activity(
                activity=K8sConfigMapCreationActivity,
                arg=K8sConfigMapCreationActivityModel(
                    namespace=tenant,
                    name=f"jeeves-{space}-config",
                    template_file_name=f"{config.env}-space-tenant-config.tmpl.json",
                    destination_file_name=space_config_file,
                    cloudflare_r2_folder_path="jeeves-config",
                    template_payload={"tenant": tenant, "space": space},
                ),
            )

            await run_activity(
                activity=K8sConfigMapCreationActivity,
                arg=K8sConfigMapCreationActivityModel(
                    namespace=tenant,
                    name="jeeves-tenant-config",
                    template_file_name=f"{config.env}-tenant-config.tmpl.json",
                    destination_file_name="tenant-config.json",
                    cloudflare_r2_folder_path="jeeves-config",
                    template_payload={"tenant": tenant, "space": space},
                ),
            )

            image_tag = "sprint"
            if config.env == "production":
                image_tag = await workflow.execute_activity(
                    activity=JeevesFetchLatestTagActivity.defn,
                    retry_policy=JeevesFetchLatestTagActivity.get_retry_policy(),
                    start_to_close_timeout=JeevesFetchLatestTagActivity.get_timeout(),
                )

            # Database migration job for space-specific schema
            docker_image = f"registry.314ecorp.tech/jeeves-app:{image_tag}"
            config_dir = "config"

            await run_activity(
                activity=KubernetesDeploymentUpdateActivity,
                arg=KubernetesDeploymentUpdateActivityModel(
                    namespace=tenant,
                    name="jeeves",
                    volume_mounts=[
                        {
                            "name": f"{space}-volume",
                            "mount_path": f"/{config_dir}/{space_config_file}",
                            "sub_path": space_config_file,
                        },
                    ],
                    volumes=[
                        {
                            "name": f"{space}-volume",
                            "config_map_name": f"jeeves-{space}-config",
                            "key": space_config_file,
                            "path": space_config_file,
                        },
                    ],
                ),
            )

            await run_activity(
                activity=KubernetesDeploymentUpdateActivity,
                arg=KubernetesDeploymentUpdateActivityModel(
                    namespace=tenant,
                    name="jeeves-worker",
                    volume_mounts=[
                        {
                            "name": f"{space}-volume",
                            "mount_path": f"/{config_dir}/{space_config_file}",
                            "sub_path": space_config_file,
                        },
                    ],
                    volumes=[
                        {
                            "name": f"{space}-volume",
                            "config_map_name": f"jeeves-{space}-config",
                            "key": space_config_file,
                            "path": space_config_file,
                        },
                    ],
                ),
            )

            await run_activity(
                activity=DatabaseMigrationJobActivity,
                arg=DatabaseMigrationJobActivityModel(
                    namespace=tenant,
                    job_name=f"jeeves-db-schema-migration-job-{space}",
                    docker_image=docker_image,
                    volume_mounts=[
                        {
                            "name": f"{space}-volume",
                            "mount_path": f"/{config_dir}/{space_config_file}",
                            "sub_path": space_config_file,
                        },
                    ],
                    volumes=[
                        {
                            "name": f"{space}-volume",
                            "config_map_name": f"jeeves-{space}-config",
                            "key": space_config_file,
                            "path": space_config_file,
                        },
                    ],
                    container_envs=[
                        {"name": "APP_CONFIG_FILE", "value": f"/{config_dir}/{space_config_file}"},
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "CLIENT_CODE", "value": tenant},
                    ],
                    argument=f"python3 /app/provisioning/dbmate_migration.py {client_name}",
                    job_type="dbmate",
                    product=ProductName,
                ),
            )

            await run_activity(
                activity=PostgresGrantAllPrivilegesOnTablesActivity,
                arg=PostgresGrantAllPrivilegesActivityModel(
                    posthog_username=jeeves_config.posthog_username,
                    database_name=postgres_database_name,
                    schema_name=postgres_schema_name,
                ),
            )

            await run_activity(
                activity=PostgresGrantAllPrivilegesOnSequencesActivity,
                arg=PostgresGrantAllPrivilegesActivityModel(
                    posthog_username=jeeves_config.posthog_username,
                    database_name=postgres_database_name,
                    schema_name=postgres_schema_name,
                ),
            )

            await run_activity(
                activity=PostgresGrantAllPrivilegesOnFunctionsActivity,
                arg=PostgresGrantAllPrivilegesActivityModel(
                    posthog_username=jeeves_config.posthog_username,
                    database_name=postgres_database_name,
                    schema_name=postgres_schema_name,
                ),
            )

            await run_activity(
                activity=PostgresGrantAllPrivilegesOnSchemaActivity,
                arg=PostgresGrantAllPrivilegesActivityModel(
                    posthog_username=jeeves_config.posthog_username,
                    database_name=postgres_database_name,
                    schema_name=postgres_schema_name,
                ),
            )

            # Keycloak Setup
            realm_name = tenant
            # Keycloak space-specific client setup
            await run_activity(
                activity=KeycloakClientSetupActivity,
                arg=KeycloakClientSetupActivityModel(
                    tenant=tenant,
                    realm_name=realm_name,
                    domain=jeeves_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_jeeves_space_client.json",
                    template_payload={"chatwoot_domain": jeeves_config.chatwoot_domain, "space": space},
                ),
            )

            roles = [
                "_access-broadcast",
                "_access-assignment",
                "_access-analytics",
                "_access-setting",
                "_allow-add-edit-asset",
                "_allow-delete-asset",
                "_allow-publish-asset",
                "_allow-standalone-launch",
                "_allow-view-asset",
                "_access-user-list",
                "_can-manage-user",
                "_developer",
                "_JEEVESALL",
            ]

            # Keycloak client roles setup
            await run_activity(
                activity=KeycloakCreateClientRolesActivity,
                arg=KeycloakCreateClientRolesActivityModel(
                    client_name=client_name,
                    realm_name=realm_name,
                    roles=roles,
                ),
            )

            # Update Keycloak client mapper with new space
            await run_activity(
                activity=KeycloakUpdateClientMapperActivity,
                arg=KeycloakUpdateClientMapperActivityModel(
                    realm_name=realm_name,
                    client_name=ProductName,
                    space_name=client_name,
                    space_display_name=space_display_name,
                ),
            )

            await run_activity(
                activity=KeycloakUpdateClientMapperActivity,
                arg=KeycloakUpdateClientMapperActivityModel(
                    realm_name=realm_name,
                    client_name="formauth",
                    space_name=client_name,
                    space_display_name=space_display_name,
                ),
            )

            # Keycloak group setup
            await run_activity(
                activity=KeycloakCreateGroupActivity,
                arg=KeycloakCreateGroupActivityModel(
                    realm_name=realm_name,
                    client_name=client_name,
                    template_path=TemplatePath,
                    template_name="keycloak_jeeves_group.json",
                    template_payload={"space": space},
                ),
            )

            # Keycloak user group setup
            await run_activity(
                activity=KeycloakCreateGroupActivity,
                arg=KeycloakCreateGroupActivityModel(
                    realm_name=realm_name,
                    client_name=client_name,
                    template_path=TemplatePath,
                    template_name="keycloak_user_group.json",
                    parent_group_name=f"{ProductName}-{space}",
                ),
            )

            # Keycloak tenant customer admin user setup
            await run_activity(
                activity=KeycloakCreateTenantCustomerAdminUserActivity,
                arg=KeycloakCreateTenantCustomerAdminUserActivityModel(
                    realm_name=realm_name,
                    client_name=client_name,
                    username=email,
                    email=email,
                    firstname=first_name,
                    lastname=last_name,
                    template_path=TemplatePath,
                    template_name="keycloak_tenant_customer_admin.json",
                    roles=[role for role in roles if role not in ["_JEEVESALL", "_developer"]],
                    group_path=f"{client_name}/Admin",
                ),
            )

            # Keycloak internal users setup
            await run_activity(
                activity=KeycloakCreateInternalUsersActivity,
                arg=KeycloakCreateInternalUsersActivityModel(
                    realm_name=realm_name,
                    client_name=client_name,
                    template_path=TemplatePath,
                    template_name="keycloak_tenant_internal_user.json",
                    users=[
                        {
                            "username": "casey.post@314ecorp.com",
                            "email": "casey.post@314ecorp.com",
                            "firstname": "Casey",
                            "lastname": "Post",
                        },
                        {
                            "username": "nick.dejongh@314ecorp.com",
                            "email": "nick.dejongh@314ecorp.com",
                            "firstname": "Nick",
                            "lastname": "DeJongh",
                        },
                        {
                            "username": "ankush.govil@314ecorp.com",
                            "email": "ankush.govil@314ecorp.com",
                            "firstname": "Ankush",
                            "lastname": "Govil",
                        },
                        {
                            "username": JeevesSystemUser,
                            "email": JeevesSystemUser,
                            "firstname": "System",
                            "lastname": "User",
                        },
                    ]
                    if config.env == "production"
                    else [
                        {
                            "username": JeevesSystemUser,
                            "email": JeevesSystemUser,
                            "firstname": "System",
                            "lastname": "User",
                        },
                        {
                            "username": "sumanth.sm@314ecorp.com",
                            "email": "sumanth.sm@314ecorp.com",
                            "firstname": "Sumanth",
                            "lastname": "S M",
                        },
                    ],
                    roles=[role for role in roles if role not in ["_JEEVESALL", "_developer"]],
                    group_path=f"{client_name}/Admin",
                ),
            )

            # Vespa Setup
            await run_activity(
                activity=VespaJobActivity,
                arg=VespaJobActivityModel(
                    jeeves=jeeves,
                    space_name=client_name,
                    image_tag=image_tag,
                ),
            )

            # Update space status to Provisioned on success
            await run_activity(
                activity=UpdateSpaceStatusActivity,
                arg=SpaceStatusModel(
                    space_name=client_name,
                    tenant_name=tenant,
                    product=ProductEnum.jeeves,
                    status=TenantStatusEnum.Provisioned,
                    error_msg=None,
                ),
            )

        except Exception as e:
            workflow.logger.error(f"Error in space creation workflow: {e=}")

            # Update space status to ProvisioningFailed on error
            try:
                await run_activity(
                    activity=UpdateSpaceStatusActivity,
                    arg=SpaceStatusModel(
                        space_name=f"{ProductName}-{space}",
                        tenant_name=tenant,
                        product=ProductEnum.jeeves,
                        status=TenantStatusEnum.ProvisioningFailed,
                        error_msg=str(e),
                    ),
                )

            except Exception as status_error:
                workflow.logger.error(f"Failed to update space status: {status_error=}")

            raise e
