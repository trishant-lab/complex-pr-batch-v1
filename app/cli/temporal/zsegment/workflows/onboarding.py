from collections.abc import Callable
from temporalio import workflow
import pydash
import orjson

from app.cli.temporal.activities.cloudflareSetup import (
    CopyArtifactsToBucketActivity,
    CopyArtifactsToBucketActivityModel,
    CreateCloudflareBucketActivity,
    CreateCloudflareBucketActivityModel,
    CreateCloudflareDNSRecordActivity,
    CreateCloudflareDNSRecordActivityModel,
    LinkBucketToDomainActivity,
    LinkBucketToDomainActivityModel,
    PropagateDNSRecordActivity,
    PropagateDNSRecordActivityModel,
)
from app.cli.temporal.activities.gitea_service import GiteaProperties
from app.cli.temporal.activities.k8snamespace import K8sNamespaceCreationActivity, K8sNamespaceCreationActivityModel
from app.cli.temporal.activities.onePassword import OnePasswordActivity, OnePasswordActivityModel
from app.cli.temporal.activities.redpanda_service import RedpandaProperties
from app.cli.temporal.activities.sendMail import (
    SendAfterProvisioningMailActivity,
    SendAfterProvisioningMailActivityModel,
    SendBeforeProvisioningMailActivity,
    SendBeforeProvisioningMailActivityModel,
)

from app.cli.temporal.activities.k8sIstioVirtualService import (
    KubernetesIstioVirtualServiceActivity,
    KubernetesIstioVirtualServiceActivityModel,
)

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

from app.cli.temporal.activities.postgresSetup import (
    PostgresSchemaCreationActivityModel,
    PostgresSchemaCreationActivity,
    PostgresUserCreationActivity,
    PostgresGrantAccessToUserActivityModel,
    PostgresGrantAccessToUserActivity,
    PostgresGrantAllPrivilegesOnTableActivity,
    PostgresUserCreationActivityModel,
)

from app.cli.temporal.activities.statefulSetPodCreation import (
    KubernetesStatefulSetActivity,
    KubernetesStatefulSetActivityModel,
)

from app.cli.temporal.zsegment import TemplatePath
from app.cli.temporal.activities.k8sconfigMap import K8sConfigMapCreationActivity, K8sConfigMapCreationActivityModel
from app.cli.temporal.activities.k8sSecret import K8sSecretCreationActivity, K8sSecretCreationActivityModel
from app.cli.temporal.activities.redis import RedisSetupActivity, RedisSetupActivityModel
from app.cli.temporal.activities.redpanda_service import RedpandaSetupActivity
from app.cli.temporal.activities.k8sService import KubernetesServiceActivity, KubernetesServiceActivityModel
from app.cli.temporal.activities.vmPodScrapper import VMPodScrapperActivity, VMPodScrapperActivityModel

from app.cli.temporal.activities.updateTenantStatus import TenantStatus, UpdateTenantStatusActivity
from app.cli.temporal.core.base import Workflow

from app.cli.temporal.activities.gitea_service import GiteaSetupActivity
from app.cli.temporal.zsegment.models.zsegmentSpec import ZSegmentSpec


with workflow.unsafe.imports_passed_through():
    from app.common import generate_password
    from app.core.settings import AppSettings, ZSegmentSettings, get_settings
    from app.onepasswordutil import OnePasswordUtil
    from app.template_env import get_env


ProductName = "zsegment"
OnePasswordVaultName = "zsegment"


@workflow.defn(name="ZSegmentOnboardingWorkflow", sandboxed=False)
class ZSegmentOnboardingWorkflow(Workflow):
    """
    ZSegment Onboarding Workflow
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
            GiteaSetupActivity.defn,
            OnePasswordActivity.defn,
            RedpandaSetupActivity.defn,
            SendAfterProvisioningMailActivity.defn,
            SendBeforeProvisioningMailActivity.defn,
            KubernetesIstioVirtualServiceActivity.defn,
            KeycloakClientSetupActivity.defn,
            KeycloakCreateClientRolesActivity.defn,
            KeycloakCreateTenantCustomerAdminUserActivity.defn,
            KeycloakRealmSetupActivity.defn,
            PostgresSchemaCreationActivity.defn,
            PostgresUserCreationActivity.defn,
            PostgresGrantAccessToUserActivity.defn,
            PostgresGrantAllPrivilegesOnTableActivity.defn,
            KubernetesStatefulSetActivity.defn,
            K8sConfigMapCreationActivity.defn,
            K8sSecretCreationActivity.defn,
            RedisSetupActivity.defn,
            KubernetesServiceActivity.defn,
            VMPodScrapperActivity.defn,
            UpdateTenantStatusActivity.defn,
            CreateCloudflareBucketActivity.defn,
            CreateCloudflareDNSRecordActivity.defn,
            LinkBucketToDomainActivity.defn,
            PropagateDNSRecordActivity.defn,
            K8sNamespaceCreationActivity.defn,
        ]

    @classmethod
    def get_workflow_id(cls: "Workflow", zsegment: ZSegmentSpec) -> str:
        """
        Return workflow id
        """
        return f"zsegment_onboarding_workflow_{pydash.get(zsegment, 'tenant')}"

    @workflow.run
    async def run(self: "Workflow", zsegment: ZSegmentSpec) -> None:
        """
        Run the workflow
        """
        config: AppSettings = get_settings()
        zsegment_config: ZSegmentSettings = config.zsegment

        first_name = pydash.get(zsegment, "firstName")
        last_name = pydash.get(zsegment, "lastName")
        email = pydash.get(zsegment, "email")
        tenant = pydash.get(zsegment, "tenant")
        realm_name = tenant

        try:
            if not pydash.get(zsegment, "emailSent"):
                await workflow.execute_activity(
                    activity=SendBeforeProvisioningMailActivity.defn,
                    arg=SendBeforeProvisioningMailActivityModel(
                        user_details={
                            "firstName": first_name,
                            "lastName": last_name,
                            "email": email,
                        },
                        product=ProductName,
                        from_name=zsegment_config.sender_name,
                        email_from=zsegment_config.sender_email,
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

            # Todo Add Activties

            # postgres setup
            postgres_dev_schema_name = f"{tenant}_dev"
            postgres_prod_schema_name = f"{tenant}_prod"
            postgres_database_name = "zsegment"
            postgres_username = f"{ProductName}_{tenant}"
            postgres_password = generate_password(length=20)
            image_tag = "production" if config.env == "production" else "sprint"
            api_docker_image = f"registry.314ecorp.tech/zsegment-api:{image_tag}"
            engine_docker_image = f"registry.314ecorp.tech/zsegment-engine:{image_tag}"

            await workflow.execute_activity(
                activity=OnePasswordActivity.defn,
                arg=OnePasswordActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item="application-config",
                    vault=OnePasswordVaultName,
                    secret_name="pg_password",
                    secret_value=postgres_password,
                ),
                retry_policy=OnePasswordActivity.get_retry_policy(),
                start_to_close_timeout=OnePasswordActivity.get_timeout(),
            )

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

            # await workflow.execute_activity(
            #     activity=PostgresSupavisorPollUserActivity.defn,
            #     arg=PostgresSupavisorPollUserActivityModel(
            #         username=postgres_username,
            #         database_name=postgres_database_name,
            #         db_password=postgres_password,
            #         template_path=TemplatePath,
            #     ),
            #     retry_policy=PostgresSupavisorPollUserActivity.get_retry_policy(),
            #     start_to_close_timeout=PostgresSupavisorPollUserActivity.get_timeout(),
            # )

            await workflow.execute_activity(
                activity=PostgresSchemaCreationActivity.defn,
                arg=PostgresSchemaCreationActivityModel(
                    schema_name=postgres_dev_schema_name,
                    username=postgres_username,
                    database_name=postgres_database_name,
                ),
                retry_policy=PostgresSchemaCreationActivity.get_retry_policy(),
                start_to_close_timeout=PostgresSchemaCreationActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=PostgresSchemaCreationActivity.defn,
                arg=PostgresSchemaCreationActivityModel(
                    schema_name=postgres_prod_schema_name,
                    username=postgres_username,
                    database_name=postgres_database_name,
                ),
                retry_policy=PostgresSchemaCreationActivity.get_retry_policy(),
                start_to_close_timeout=PostgresSchemaCreationActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=PostgresGrantAccessToUserActivity.defn,
                arg=PostgresGrantAccessToUserActivityModel(
                    schema_name=postgres_dev_schema_name,
                    username=postgres_username,
                    database_name=postgres_database_name,
                ),
                retry_policy=PostgresGrantAccessToUserActivity.get_retry_policy(),
                start_to_close_timeout=PostgresGrantAccessToUserActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=PostgresGrantAccessToUserActivity.defn,
                arg=PostgresGrantAccessToUserActivityModel(
                    schema_name=postgres_prod_schema_name,
                    username=postgres_username,
                    database_name=postgres_database_name,
                ),
                retry_policy=PostgresGrantAccessToUserActivity.get_retry_policy(),
                start_to_close_timeout=PostgresGrantAccessToUserActivity.get_timeout(),
            )

            # await workflow.execute_activity(
            #     activity=KeycloakUserMappingActivity.defn,
            #     arg=KeycloakUserMappingActivityModel(
            #         username=postgres_username,
            #         database_name=postgres_database_name,
            #     ),
            #     retry_policy=KeycloakUserMappingActivity.get_retry_policy(),
            #     start_to_close_timeout=KeycloakUserMappingActivity.get_timeout(),
            # )

            # await workflow.execute_activity(
            #     activity=MatomoUserMappingActivity.defn,
            #     arg=MatomoUserMappingActivityModel(
            #         username=postgres_username,
            #         database_name=postgres_database_name,
            #     ),
            #     retry_policy=MatomoUserMappingActivity.get_retry_policy(),
            #     start_to_close_timeout=MatomoUserMappingActivity.get_timeout(),
            # )

            # await workflow.execute_activity(
            #     activity=PostgresGrantAllPrivilegesOnTableActivity.defn,
            #     arg=PostgresGrantAllPrivilegesOnTableActivityModel(
            #         database_name=postgres_database_name,
            #         username=postgres_username,
            #         tables=[
            #             "user_entity",
            #             "realm",
            #             "user_attribute",
            #             "keycloak_role",
            #             "user_role_mapping",
            #             # "matomo_log_visit",
            #             # "matomo_log_action",
            #             # "matomo_log_media",
            #             # "matomo_log_link_visit_action",
            #             # "matomo_log_visit_view",
            #             # "matomo_log_action_view",
            #             # "matomo_log_media_view",
            #             # "matomo_log_link_visit_action_view",
            #         ],
            #     ),
            #     retry_policy=PostgresGrantAllPrivilegesOnTableActivity.get_retry_policy(),
            #     start_to_close_timeout=PostgresGrantAllPrivilegesOnTableActivity.get_timeout(),
            # )
            installer_secret = generate_password(length=20)

            # keycloak realm setup
            await workflow.execute_activity(
                activity=KeycloakRealmSetupActivity.defn,
                arg=KeycloakRealmSetupActivityModel(
                    tenant=tenant,
                    domain=zsegment_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_realm.json",
                    installer_secret=installer_secret,
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
                    domain=zsegment_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_client.json",
                ),
                retry_policy=KeycloakClientSetupActivity.get_retry_policy(),
                start_to_close_timeout=KeycloakClientSetupActivity.get_timeout(),
            )

            roles = [
                "_admin",
                "_dev_default-users",
                "_dev_manage-connector",
                "_dev_manage-credentials",
                "_dev_manage-default-users",
                "_dev_manage-interface-migrations",
                "_dev_manage-libraries",
                "_dev_manage-messages",
                "_dev_manage-metric-dashboard",
                "_dev_manage-tasks",
                "_prod_default-users",
                "_prod_manage-connector",
                "_prod_manage-credentials",
                "_prod_manage-default-users",
                "_prod_manage-interface-migrations",
                "_prod_manage-libraries",
                "_prod_manage-messages",
                "_prod_manage-metric-dashboard",
                "_prod_manage-tasks",
            ]
            # keycloak client roles setup
            await workflow.execute_activity(
                activity=KeycloakCreateClientRolesActivity.defn,
                arg=KeycloakCreateClientRolesActivityModel(
                    client_name="zsegment",
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
                    client_name="zsegment",
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

            # # keycloak internal users setup
            # await workflow.execute_activity(
            #     activity=KeycloakCreateInternalUsersActivity.defn,
            #     arg=KeycloakCreateInternalUsersActivityModel(
            #         realm_name=realm_name,
            #         client_name="zsegment",
            #         template_path=TemplatePath,
            #         template_name="keycloak_tenant_internal_user.json",
            #     ),
            #     retry_policy=KeycloakCreateInternalUsersActivity.get_retry_policy(),
            #     start_to_close_timeout=KeycloakCreateInternalUsersActivity.get_timeout(),
            # )

            await workflow.execute_activity(
                activity=K8sNamespaceCreationActivity.defn,
                arg=K8sNamespaceCreationActivityModel(
                    namespace=tenant,
                ),
                retry_policy=K8sNamespaceCreationActivity.get_retry_policy(),
                start_to_close_timeout=K8sNamespaceCreationActivity.get_timeout(),
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

            # setup redpanda
            redpanda_tenant_password = generate_password(length=20)
            OnePasswordUtil(
                tenant=f"{ProductName}_{tenant}",
                server_item="application-config",
                vault=OnePasswordVaultName,
            ).create_or_replace("redpanda_password", redpanda_tenant_password)

            await workflow.execute_activity(
                activity=RedpandaSetupActivity.defn,
                arg=RedpandaProperties(
                    tenant=tenant,
                    environment=config.env,
                    broker=zsegment_config.redpanda_broker,
                    admin_username=zsegment_config.redpanda_admin_username,
                    admin_password=zsegment_config.redpanda_admin_password,
                    tenant_password=redpanda_tenant_password,
                    admin_api_base_url=zsegment_config.redpanda_admin_api_base_url,
                ),
                retry_policy=RedpandaSetupActivity.get_retry_policy(),
                start_to_close_timeout=RedpandaSetupActivity.get_timeout(),
            )

            # setup gitea
            gitea_base_url = (zsegment_config.gitea_base_url,)
            gitea_admin_username = (zsegment_config.gitea_admin_username,)
            gitea_admin_password = (zsegment_config.gitea_admin_password,)
            gitea_template_owner = (zsegment_config.gitea_template_owner,)

            await workflow.execute_activity(
                activity=GiteaSetupActivity.defn,
                arg=GiteaProperties(
                    tenant=tenant,
                    email=email,
                    base_url=gitea_base_url,
                    admin_username=gitea_admin_username,
                    admin_password=gitea_admin_password,
                    template_repo="ZSegmentTemplate",
                    template_owner=gitea_template_owner,
                ),
                retry_policy=GiteaSetupActivity.get_retry_policy(),
                start_to_close_timeout=GiteaSetupActivity.get_timeout(),
            )

            # setup dev-api configmap
            await workflow.execute_activity(
                activity=K8sConfigMapCreationActivity.defn,
                arg=K8sConfigMapCreationActivityModel(
                    namespace=tenant,
                    name="dev-api-config",
                    template_file_name="api-config.json",
                    bucket_name="zsegment-config",
                    template_payload={
                        "tenantName": tenant,
                        "environment": "dev",
                        "server-environment": config.env.upper(),
                        "keycloakRealm": realm_name,
                        "KeycloakAuthServerUrl": "https://auth.314ecorp.tech/auth",
                        "keycloakSecret": installer_secret,  # Need discussion
                        "redpandaBrokerUrl": zsegment_config.redpanda_broker,  # Need discussion
                        "redpandaPassword": redpanda_tenant_password,
                        "lagoUrl": config.lago_url,  # Need discussion
                        "lagoKey": config.lago_key,  # Need discussion
                        "lagoCustomerId": config.lago_customer_id,  # Need discussion
                        "lokiPushUrl": "http://loki.monitoring-system.svc.cluster.local:3100",
                        "victoriaMetricsUrl": "http://vmselect-vm-cluster.monitoring-system.svc.cluster.local:8481/select/0/prometheus",
                        "postgresUrl": "db-cluster-ha.postgresql.svc.cluster.local",
                        "postgresSecret": postgres_password,
                        "gitea_api_base_url": config.gitea_api_base_url,  # Need discussion
                        "gitea_api_repo_url": config.gitea_api_repo_url,  # Need discussion
                        "gitea_admin_username": config.gitea_admin_username,  # Need discussion
                        "gitea_admin_password": config.gitea_admin_password,  # Need discussion
                        "redisPassword": redis_tenant_password,
                        "matomoAuthToken": "e9c5ba18c4d7af04c4fdb1443d604e88&force_api_session=1",
                    },
                ),
            )

            # setup dev-engine configmap
            await workflow.execute_activity(
                activity=K8sConfigMapCreationActivity.defn,
                arg=K8sConfigMapCreationActivityModel(
                    namespace=tenant,
                    name="dev-engine-config",
                    template_file_name="engine-config.json",
                    bucket_name="zsegment-config",
                    template_payload={
                        "tenantName": tenant,
                        "environment": "dev",
                        "redpandaBrokerUrl": config.broker_url,  # Need discussion
                        "redpandaPassword": config.password,  # Need discussion
                        "lagoUrl": config.lago_url,  # Need discussion
                        "lagoKey": config.lago_key,  # Need discussion
                        "lagoCustomerId": config.lago_customer_id,  # Need discussion
                        "postgresUrl": "db-cluster-ha.postgresql.svc.cluster.local",
                        "postgresSecret": config.secret_name,  # Need discussion
                        "gitea_admin_username": config.gitea_admin_username,  # Need discussion
                        "gitea_admin_password": config.gitea_admin_password,  # Need discussion
                        "redisPassword": config.redis_password,  # Need discussion
                    },
                ),
            )

            # dns setup for api
            await workflow.execute_activity(
                activity=CreateCloudflareDNSRecordActivity.defn,
                arg=CreateCloudflareDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{zsegment_config.domain_name}",
                    zone_id=zsegment_config.zone_id,
                ),
                retry_policy=CreateCloudflareDNSRecordActivity.get_retry_policy(),
                start_to_close_timeout=CreateCloudflareDNSRecordActivity.get_timeout(),
            )

            # create bucket
            bucket_name = f"{tenant}-{zsegment_config.domain_name.replace('.', '-')}"
            await workflow.execute_activity(
                activity=CreateCloudflareBucketActivity.defn,
                arg=CreateCloudflareBucketActivityModel(
                    bucket_name=bucket_name,
                ),
                retry_policy=CreateCloudflareBucketActivity.get_retry_policy(),
                start_to_close_timeout=CreateCloudflareBucketActivity.get_timeout(),
            )

            # link bucket to custom domain
            await workflow.execute_activity(
                activity=LinkBucketToDomainActivity.defn,
                arg=LinkBucketToDomainActivityModel(
                    bucket_name=bucket_name,
                    domain_name=f"{tenant}.{zsegment_config.domain_name}",
                    zone_id=zsegment_config.zone_id,
                ),
                retry_policy=LinkBucketToDomainActivity.get_retry_policy(),
                start_to_close_timeout=LinkBucketToDomainActivity.get_timeout(),
            )

            # propagate the dns record
            await workflow.execute_activity(
                activity=PropagateDNSRecordActivity.defn,
                arg=PropagateDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{zsegment_config.domain_name}",
                ),
                retry_policy=PropagateDNSRecordActivity.get_retry_policy(),
                start_to_close_timeout=PropagateDNSRecordActivity.get_timeout(),
            )

            # ui setup
            repo_name = "zsegment-ui"
            image_tag = "production" if config.env == "production" else "sprint"

            if config.env == "production":
                dest_dir = f"{tenant}.{zsegment_config.domain_name}/"
            else:
                dest_dir = f"{tenant}.{zsegment_config.domain_name}/{image_tag}"

            src_object_name = f"{repo_name}/{image_tag}/bundle.zip"

            bundle_path = "bundle/dist/admin"

            # copy artifacts to bucket
            await workflow.execute_activity(
                activity=CopyArtifactsToBucketActivity.defn,
                arg=CopyArtifactsToBucketActivityModel(
                    bucket_name=bucket_name,
                    src_object_name=src_object_name,
                    dest_dir=dest_dir,
                    bundle_path=bundle_path,
                    bundle_name="bundle.zip",
                    tenant=tenant,
                ),
                retry_policy=CopyArtifactsToBucketActivity.get_retry_policy(),
                start_to_close_timeout=CopyArtifactsToBucketActivity.get_timeout(),
            )

            # dns setup
            # await workflow.execute_activity(
            #     activity=DnsSetupActivity.defn,
            #     arg=DnsSetupActivityModel(
            #         cname=config.google_dns_cname,
            #         fqdn=f"{tenant}.{zsegment_config.domain_name}.",
            #         zone_name=zsegment_config.zone_name,
            #     ),
            #     retry_policy=DnsSetupActivity.get_retry_policy(),
            #     start_to_close_timeout=DnsSetupActivity.get_timeout(),
            # )

            # # ui setup
            # repo_name = "zsegment-ui"
            # image_tag = "production" if config.env == "production" else "sprint"

            # if config.env == "production":
            #     dest_dir = f"{tenant}.{zsegment_config.domain_name}/"
            # else:
            #     dest_dir = f"{tenant}.{zsegment_config.domain_name}/{image_tag}"

            # src_object_name = f"{repo_name}/{image_tag}/bundle.zip"

            # bundle_path = "bundle/dist/admin"

            # await workflow.execute_activity(
            #     activity=UiSetupActivity.defn,
            #     arg=UiSetupActivityModel(
            #         src_object_name=src_object_name,
            #         dest_dir=dest_dir,
            #         bundle_path=bundle_path,
            #     ),
            #     retry_policy=UiSetupActivity.get_retry_policy(),
            #     start_to_close_timeout=UiSetupActivity.get_timeout(),
            # )

            # statefulset pod creation for server
            await workflow.execute_activity(
                activity=KubernetesStatefulSetActivity.defn,
                arg=KubernetesStatefulSetActivityModel(
                    namespace=tenant,
                    name="zsegment-api-dev",
                    docker_image=api_docker_image,
                    request_resource={
                        "cpu": pydash.get(zsegment, "serverSpec.request_cpu"),
                        "memory": pydash.get(zsegment, "serverSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(zsegment, "serverSpec.limit_cpu"),
                        "memory": pydash.get(zsegment, "serverSpec.limit_memory"),
                    },
                    container_ports=[8090],
                    volume_mounts=[
                        {
                            "name": "tenant-volume",
                            "mount_path": "/config/api-config.json",
                            "sub_path": "api-config.json",
                        },
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "zsegment-tenant-config",
                            "key": "api-config.json",
                            "path": "api-config.json",
                        }
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "WEB_CONCURRENCY", "value": "5"},
                        {"name": "CLIENT_CODE", "value": tenant},
                        {"name": "APP_CONFIG_FILE", "value": "/config/api-config.json"},
                        {"name": "POSTGRES_PASSWORD", "value": postgres_password},
                        {"name": "POSTGRES_USER", "value": postgres_username},
                        {"name": "EXTRACTOR_ENABLED", "value": "FALSE"},
                        {"name": "DYNAMIC_URL_ENABLED", "value": "True"},
                    ],
                ),
                retry_policy=KubernetesStatefulSetActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesStatefulSetActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=KubernetesStatefulSetActivity.defn,
                arg=KubernetesStatefulSetActivityModel(
                    namespace=tenant,
                    name="zsegment-api-prod",
                    docker_image=api_docker_image,
                    request_resource={
                        "cpu": pydash.get(zsegment, "serverSpec.request_cpu"),
                        "memory": pydash.get(zsegment, "serverSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(zsegment, "serverSpec.limit_cpu"),
                        "memory": pydash.get(zsegment, "serverSpec.limit_memory"),
                    },
                    container_ports=[8090],
                    volume_mounts=[
                        {
                            "name": "tenant-volume",
                            "mount_path": "/config/api-config.json",
                            "sub_path": "api-config.json",
                        },
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "zsegment-tenant-config",
                            "key": "api-config.json",
                            "path": "api-config.json",
                        }
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "WEB_CONCURRENCY", "value": "5"},
                        {"name": "CLIENT_CODE", "value": tenant},
                        {"name": "APP_CONFIG_FILE", "value": "/config/api-config.json"},
                        {"name": "POSTGRES_PASSWORD", "value": postgres_password},
                        {"name": "POSTGRES_USER", "value": postgres_username},
                        {"name": "EXTRACTOR_ENABLED", "value": "FALSE"},
                        {"name": "DYNAMIC_URL_ENABLED", "value": "True"},
                    ],
                ),
                retry_policy=KubernetesStatefulSetActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesStatefulSetActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=KubernetesStatefulSetActivity.defn,
                arg=KubernetesStatefulSetActivityModel(
                    namespace=tenant,
                    name="zsegment-engine-dev",
                    docker_image=engine_docker_image,
                    request_resource={
                        "cpu": pydash.get(zsegment, "serverSpec.request_cpu"),
                        "memory": pydash.get(zsegment, "serverSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(zsegment, "serverSpec.limit_cpu"),
                        "memory": pydash.get(zsegment, "serverSpec.limit_memory"),
                    },
                    container_ports=[8089],
                    volume_mounts=[
                        {
                            "name": "tenant-volume",
                            "mount_path": "/config/engine-config.json",
                            "sub_path": "engine-config.json",
                        },
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "zsegment-tenant-config",
                            "key": "engine-config.json",
                            "path": "engine-config.json",
                        }
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "WEB_CONCURRENCY", "value": "5"},
                        {"name": "CLIENT_CODE", "value": tenant},
                        {"name": "APP_CONFIG_FILE", "value": "/config/api-config.json"},
                        {"name": "POSTGRES_PASSWORD", "value": postgres_password},
                        {"name": "POSTGRES_USER", "value": postgres_username},
                        {"name": "EXTRACTOR_ENABLED", "value": "FALSE"},
                        {"name": "DYNAMIC_URL_ENABLED", "value": "True"},
                    ],
                ),
                retry_policy=KubernetesStatefulSetActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesStatefulSetActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=KubernetesStatefulSetActivity.defn,
                arg=KubernetesStatefulSetActivityModel(
                    namespace=tenant,
                    name="zsegment-engine-prod",
                    docker_image=engine_docker_image,
                    request_resource={
                        "cpu": pydash.get(zsegment, "serverSpec.request_cpu"),
                        "memory": pydash.get(zsegment, "serverSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(zsegment, "serverSpec.limit_cpu"),
                        "memory": pydash.get(zsegment, "serverSpec.limit_memory"),
                    },
                    container_ports=[8089],
                    volume_mounts=[
                        {
                            "name": "tenant-volume",
                            "mount_path": "/config/engine-config.json",
                            "sub_path": "engine-config.json",
                        },
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "zsegment-tenant-config",
                            "key": "engine-config.json",
                            "path": "engine-config.json",
                        }
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "WEB_CONCURRENCY", "value": "5"},
                        {"name": "CLIENT_CODE", "value": tenant},
                        {"name": "APP_CONFIG_FILE", "value": "/config/api-config.json"},
                        {"name": "POSTGRES_PASSWORD", "value": postgres_password},
                        {"name": "POSTGRES_USER", "value": postgres_username},
                        {"name": "EXTRACTOR_ENABLED", "value": "FALSE"},
                        {"name": "DYNAMIC_URL_ENABLED", "value": "True"},
                    ],
                ),
                retry_policy=KubernetesStatefulSetActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesStatefulSetActivity.get_timeout(),
            )

            # vm pod scraper
            await workflow.execute_activity(
                activity=VMPodScrapperActivity.defn,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="zsegment-api-metrics-dev",
                    app="zsegment-api-dev",
                    path="/api/v1/dev/actuator/prometheus",
                    interval="5s",
                ),
                retry_policy=VMPodScrapperActivity.get_retry_policy(),
                start_to_close_timeout=VMPodScrapperActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=VMPodScrapperActivity.defn,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="zsegment-api-metrics-prod",
                    app="zsegment-api-prod",
                    path="/api/v1/prod/actuator/prometheus",
                    interval="5s",
                ),
                retry_policy=VMPodScrapperActivity.get_retry_policy(),
                start_to_close_timeout=VMPodScrapperActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=VMPodScrapperActivity.defn,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="zsegment-engine-metrics-dev",
                    app="zsegment-engine-dev",
                    path="/api/v1/dev/actuator/prometheus",
                    interval="5s",
                ),
                retry_policy=VMPodScrapperActivity.get_retry_policy(),
                start_to_close_timeout=VMPodScrapperActivity.get_timeout(),
            )

            await workflow.execute_activity(
                activity=VMPodScrapperActivity.defn,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="zsegment-engine-metrics-prod",
                    app="zsegment-engine-prod",
                    path="/api/v1/prod/actuator/prometheus",
                    interval="5s",
                ),
                retry_policy=VMPodScrapperActivity.get_retry_policy(),
                start_to_close_timeout=VMPodScrapperActivity.get_timeout(),
            )

            # kubernetes service
            # For Dev
            await workflow.execute_activity(
                activity=KubernetesServiceActivity.defn,
                arg=KubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="zsegment-api-dev",
                    port=8090,
                ),
                retry_policy=KubernetesServiceActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesServiceActivity.get_timeout(),
            )

            # For Prod
            await workflow.execute_activity(
                activity=KubernetesServiceActivity.defn,
                arg=KubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="zsegment-api-prod",
                    port=8090,
                ),
                retry_policy=KubernetesServiceActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesServiceActivity.get_timeout(),
            )

            # VS for dev
            template_env = get_env(template_path=TemplatePath)

            template = template_env.get_template("istio-rules-dev.json")
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
            await workflow.execute_activity(
                activity=KubernetesIstioVirtualServiceActivity.defn,
                arg=KubernetesIstioVirtualServiceActivityModel(
                    namespace=tenant,
                    host=f"{tenant}.{zsegment_config.domain_name}",
                    service_name="zsegment-api-dev-vs",
                    payload=http_list,
                ),
                retry_policy=KubernetesIstioVirtualServiceActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesIstioVirtualServiceActivity.get_timeout(),
            )

            # vs for prod
            template = template_env.get_template("istio-rules-prod.json")
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

            await workflow.execute_activity(
                activity=KubernetesIstioVirtualServiceActivity.defn,
                arg=KubernetesIstioVirtualServiceActivityModel(
                    namespace=tenant,
                    host=f"{tenant}.{zsegment_config.domain_name}",
                    service_name="zsegment-api-prod-vs",
                    payload=http_list,
                ),
                retry_policy=KubernetesIstioVirtualServiceActivity.get_retry_policy(),
                start_to_close_timeout=KubernetesIstioVirtualServiceActivity.get_timeout(),
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
                    domain_name=zsegment_config.domain_name,
                    product=ProductName,
                    from_name=zsegment_config.sender_name,
                    email_from=zsegment_config.sender_email,
                ),
                retry_policy=SendAfterProvisioningMailActivity.get_retry_policy(),
                start_to_close_timeout=SendAfterProvisioningMailActivity.get_timeout(),
            )

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
