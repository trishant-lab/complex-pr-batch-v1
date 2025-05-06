from collections.abc import Callable
from uuid import uuid4
import os

import pydash
from temporalio import workflow

from app.cli.activity_util import run_activity
from app.cli.temporal.activities.cloudflare_setup import (
    CopyArtifactsToBucketActivity,
    CreateCloudflareBucketActivity,
    CreateCloudflareDNSRecordActivity,
    LinkBucketToDomainActivity,
    PropagateDNSRecordActivity,
)
from app.cli.temporal.activities.deployment_pod_creation import (
    KubernetesDeploymentActivity,
    KubernetesDeploymentActivityModel,
)
from app.cli.temporal.activities.droplet_setup import (
    CreateDropletActivity,
)
from app.cli.temporal.activities.gitea_service import (
    GiteaProperties,
    GiteaService,
    GiteaSetupActivity,
)
from app.cli.temporal.activities.k8s_config_map import (
    K8sConfigMapCreationActivity,
    K8sConfigMapCreationActivityModel,
)
from app.cli.temporal.activities.k8s_istio_virtual_service import (
    KubernetesIstioVirtualServiceActivity,
    KubernetesIstioVirtualServiceActivityModel,
)
from app.cli.temporal.activities.k8s_namespace import (
    K8sNamespaceCreationActivity,
    K8sNamespaceCreationActivityModel,
)
from app.cli.temporal.activities.k8s_secret import (
    K8sSecretCreationActivity,
    K8sSecretCreationActivityModel,
)
from app.cli.temporal.activities.k8s_service import (
    KubernetesServiceActivity,
    KubernetesServiceActivityModel,
)
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
from app.cli.temporal.activities.lago_service import LagoProperties, LagoSetupActivity
from app.cli.temporal.activities.one_password import (
    OnePasswordCreateOrUpdateActivity,
    OnePasswordCreateOrUpdateActivityModel,
    OnePasswordGetActivity,
    OnePasswordGetActivityModel,
)
from app.cli.temporal.activities.postgres_setup import (
    PostgresGrantAccessToUserActivity,
    PostgresGrantAccessToUserActivityModel,
    PostgresGrantAllPrivilegesOnTableActivity,
    PostgresSchemaCreationActivity,
    PostgresSchemaCreationActivityModel,
    PostgresUserCreationActivity,
    PostgresUserCreationActivityModel,
)
from app.cli.temporal.activities.redis import (
    RedisSetupActivity,
    RedisSetupActivityModel,
)
from app.cli.temporal.activities.redpanda_service import RedpandaProperties, RedpandaSetupActivity
from app.cli.temporal.activities.send_mail import (
    SendAfterProvisioningMailActivity,
    SendAfterProvisioningMailActivityModel,
    SendBeforeProvisioningMailActivity,
    SendBeforeProvisioningMailActivityModel,
)
from app.cli.temporal.activities.service_account_setup import (
    CreateKubernetesResourcesActivity,
    CreateKubernetesResourcesActivityModel,
)
from app.cli.temporal.activities.stateful_set_pod_creation import (
    CheckPodRunningStatusActivity,
    CheckPodRunningStatusActivityModel,
)
from app.cli.temporal.activities.update_tenant_status import (
    TenantCliStatus,
    UpdateTenantStatusActivity,
)
from app.cli.temporal.activities.vm_pod_scrapper import (
    VMPodScrapperActivity,
    VMPodScrapperActivityModel,
)
from app.cli.temporal.core.base import Workflow
from app.cli.temporal.models.cloudflare import (
    CopyArtifactsToBucketActivityModel,
    CreateCloudflareBucketActivityModel,
    CreateCloudflareDNSRecordActivityModel,
    LinkBucketToDomainActivityModel,
    PropagateDNSRecordActivityModel,
)
from app.cli.temporal.zsegment import TemplatePath
from app.cli.temporal.zsegment.models.zsegment_spec import ZSegmentSpec
from app.core.ijson import ijson_loads
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum

with workflow.unsafe.imports_passed_through():
    from app.common import generate_password
    from app.core.settings import AppSettings, ZSegmentSettings, get_settings
    from app.template_env import get_env

# Import the GrafanaDashboard components
from app.cli.temporal.activities.grafana_dashboard import GrafanaDashboardActivity, GrafanaDashboardProperties

ProductName = "zsegment"
OnePasswordVaultName = "zsegment"


@workflow.defn(name="ZSegmentOnboardingWorkflow", sandboxed=False)
class ZSegmentOnboardingWorkflow(Workflow):
    """
    ZSegment Onboarding Workflow
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
            GiteaSetupActivity.defn,
            OnePasswordCreateOrUpdateActivity.defn,
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
            KubernetesDeploymentActivity.defn,
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
            LagoSetupActivity.defn,
            CopyArtifactsToBucketActivity.defn,
            OnePasswordGetActivity.defn,
            CreateKubernetesResourcesActivity.defn,
            CheckPodRunningStatusActivity.defn,
            CreateDropletActivity.defn,
            GrafanaDashboardActivity.defn,
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
        realm_name = f"{tenant}"

        template_env = get_env(template_path=TemplatePath)

        try:
            if not pydash.get(zsegment, "emailSent"):
                await run_activity(
                    activity=SendBeforeProvisioningMailActivity,
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
                        product=ProductEnum.zsegment,
                    ),
                )

            # postgres setup
            postgres_schema_name = f"{tenant}"
            postgres_database_name = "zsegment"
            postgres_username = f"{ProductName}_{tenant}"
            postgres_password = generate_password(length=20)
            image_tag = "production" if config.env == "production" else "sprint"
            api_docker_image = f"registry.314ecorp.tech/zsegment-api:{image_tag}"
            engine_docker_image = f"registry.314ecorp.tech/zsegment-engine:{image_tag}"

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item="application-config",
                    vault=OnePasswordVaultName,
                    secret_name="pg_password",
                    secret_value=postgres_password,
                ),
            )

            await run_activity(
                activity=PostgresUserCreationActivity,
                arg=PostgresUserCreationActivityModel(
                    username=postgres_username,
                    database_name=postgres_database_name,
                    password=postgres_password,
                ),
            )

            await run_activity(
                activity=PostgresSchemaCreationActivity,
                arg=PostgresSchemaCreationActivityModel(
                    schema_name=postgres_schema_name,
                    username=postgres_username,
                    database_name=postgres_database_name,
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

            installer_secret = await run_activity(
                activity=OnePasswordGetActivity,
                arg=OnePasswordGetActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item="application-config",
                    vault=OnePasswordVaultName,
                    secret_name="installer_secret",
                ),
            )

            installer_secret = generate_password(length=20) if not installer_secret else installer_secret

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item="application-config",
                    vault=OnePasswordVaultName,
                    secret_name="installer_secret",
                    secret_value=installer_secret,
                ),
            )

            # keycloak realm setup
            await run_activity(
                activity=KeycloakRealmSetupActivity,
                arg=KeycloakRealmSetupActivityModel(
                    realm_name=realm_name,
                    domain=zsegment_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_realm.json",
                    installer_secret=installer_secret,
                ),
            )

            # keycloak client setup
            await run_activity(
                activity=KeycloakClientSetupActivity,
                arg=KeycloakClientSetupActivityModel(
                    tenant=tenant,
                    realm_name=realm_name,
                    domain=zsegment_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_client.json",
                ),
            )

            # keycloak client setup
            await run_activity(
                activity=KeycloakClientSetupActivity,
                arg=KeycloakClientSetupActivityModel(
                    tenant="installer",
                    realm_name=realm_name,
                    domain=zsegment_config.domain_name,
                    template_path=TemplatePath,
                    template_name="keycloak_installer_client.json",
                    template_payload={
                        "installer_secret": installer_secret,
                    },
                ),
            )

            roles = [
                "_admin",
                "_default-users",
                "_manage-connector",
                "_manage-credentials",
                "_manage-default-users",
                "_manage-interface-migrations",
                "_manage-libraries",
                "_manage-messages",
                "_manage-metric-dashboard",
                "_manage-tasks",
            ]
            # keycloak client roles setup
            await run_activity(
                activity=KeycloakCreateClientRolesActivity,
                arg=KeycloakCreateClientRolesActivityModel(
                    client_name="zsegment",
                    realm_name=realm_name,
                    roles=roles,
                ),
            )

            # keycloak tenant customer admin user setup
            await run_activity(
                activity=KeycloakCreateTenantCustomerAdminUserActivity,
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

            # secret setup for redis password
            await run_activity(
                activity=K8sSecretCreationActivity,
                arg=K8sSecretCreationActivityModel(
                    namespace=tenant,
                    name="cache-secret",
                    string_data={"REDIS_PASSWORD": config.cache_admin_password},
                ),
            )

            # setup redis
            redis_tenant_password = generate_password(length=20)

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

            ## setup redpanda
            redpanda_tenant_password = generate_password(length=20)

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item="application-config",
                    vault=OnePasswordVaultName,
                    secret_name="redpanda_password",
                    secret_value=redpanda_tenant_password,
                ),
            )

            await run_activity(
                activity=RedpandaSetupActivity,
                arg=RedpandaProperties(
                    tenant=tenant,
                    environment=config.env,
                    broker=zsegment_config.redpanda_broker,
                    admin_username=zsegment_config.redpanda_admin_username,
                    admin_password=zsegment_config.redpanda_admin_password,
                    tenant_password=redpanda_tenant_password,
                    admin_api_base_url=zsegment_config.redpanda_admin_api_base_url,
                ),
            )

            # setup gitea
            gitea_base_url = zsegment_config.gitea_base_url
            gitea_admin_username = zsegment_config.gitea_admin_username
            gitea_admin_password = zsegment_config.gitea_admin_password
            gitea_template_owner = zsegment_config.gitea_template_owner

            await run_activity(
                activity=GiteaSetupActivity,
                arg=GiteaProperties(
                    tenant=tenant,
                    email=email,
                    base_url=gitea_base_url,
                    admin_username=gitea_admin_username,
                    admin_password=gitea_admin_password,
                    template_repo="ZSegmentTemplate",
                    template_owner=gitea_template_owner,
                ),
            )

            # setup lago
            lago_customer_id = uuid4()
            lago_subscription_id = uuid4()
            lago_plan_code = pydash.get(zsegment, "planName", "Free")
            lago_api_key = zsegment_config.lago.api_key
            lago_api_url = zsegment_config.lago.api_url

            await run_activity(
                activity=OnePasswordCreateOrUpdateActivity,
                arg=OnePasswordCreateOrUpdateActivityModel(
                    tenant=f"{ProductName}_{tenant}",
                    server_item="application-config",
                    vault=OnePasswordVaultName,
                    secret_name="lago_customer_id",
                    secret_value=str(lago_customer_id),
                ),
            )

            await run_activity(
                activity=LagoSetupActivity,
                arg=LagoProperties(
                    tenant=tenant,
                    customer_id=lago_customer_id,
                    customer_name=tenant,
                    customer_email=email,
                    subscription_id=lago_subscription_id,
                    plan_code=lago_plan_code,
                    api_key=lago_api_key,
                    api_url=lago_api_url,
                ),
            )

            gitea_username = GiteaService.extract_username(email)
            gitea_repo_url = f"/repos/{zsegment_config.gitea_admin_username}/{tenant}/"
            # setup api-dev-config
            api_config = "api-config.json"
            engine_config = "engine-config.json"
            config_dir = "config"

            await run_activity(
                activity=K8sConfigMapCreationActivity,
                arg=K8sConfigMapCreationActivityModel(
                    namespace=tenant,
                    name="zsegment-api-config",
                    template_file_name=f"{config.env}-api-config.tmpl.json",
                    destination_file_name=api_config,
                    bucket_name="zsegment-config",
                    template_payload={
                        "tenantName": tenant,
                        "server_environment": config.env.upper(),
                        "keycloakRealm": realm_name,
                        "KeycloakAuthServerUrl": zsegment_config.keycloak_auth_server_url,
                        "keycloakSecret": installer_secret,
                        "redpandaBrokerUrl": zsegment_config.redpanda_broker,
                        "redpandaPassword": redpanda_tenant_password,
                        "lagoUrl": zsegment_config.lago.api_url,
                        "lagoKey": zsegment_config.lago.api_key,
                        "lagoCustomerId": lago_customer_id,
                        "lokiPushUrl": "http://loki.monitoring-system.svc.cluster.local:3100",  # NOSONAR
                        "victoriaMetricsUrl": zsegment_config.victoria_metrics_url,
                        "postgresUrl": zsegment_config.postgres_url,
                        "postgresSecret": postgres_password,
                        "gitea_api_base_url": zsegment_config.gitea_base_url,
                        "gitea_api_repo_url": gitea_repo_url,
                        "gitea_admin_username": zsegment_config.gitea_admin_username,
                        "gitea_admin_password": zsegment_config.gitea_admin_password,
                        "redisPassword": redis_tenant_password,
                        "matomoAuthToken": zsegment_config.matomo_auth_token,
                        "giteaUserName": gitea_username,
                        "dockerSecret": "registrycred",
                        "codeServerHost": f"{tenant}.cs.{zsegment_config.domain_name}",
                        "codeServerAlllowedOrigin": f"https://{tenant}.{zsegment_config.domain_name}",
                        "webhookSecret": "abcdefghijkl",
                        "jgitApiServiceUrl": (
                            f"http://zsegment-api.{tenant}.svc.cluster.local:8090/api/v1/git/webhook"  # NOSONAR
                        ),
                        "digitaloceanToken": zsegment_config.digital_ocean_token,
                        "omniflowServerUrl": zsegment_config.omniflow_server_url,
                    },
                ),
            )

            # setup engine-dev-config
            await run_activity(
                activity=K8sConfigMapCreationActivity,
                arg=K8sConfigMapCreationActivityModel(
                    namespace=tenant,
                    name="zsegment-engine-config",
                    template_file_name=f"{config.env}-engine-config.tmpl.json",
                    destination_file_name=engine_config,
                    bucket_name="zsegment-config",
                    template_payload={
                        "tenantName": tenant,
                        "redpandaBrokerUrl": zsegment_config.redpanda_broker,
                        "redpandaPassword": redpanda_tenant_password,
                        "lagoUrl": zsegment_config.lago.api_url,
                        "lagoKey": zsegment_config.lago.api_key,
                        "lagoCustomerId": lago_customer_id,
                        "postgresUrl": zsegment_config.postgres_url,
                        "postgresSecret": postgres_password,
                        "gitea_admin_username": zsegment_config.gitea_admin_username,
                        "gitea_admin_password": zsegment_config.gitea_admin_password,
                        "redisPassword": redis_tenant_password,
                        "giteaUserName": gitea_username,
                    },
                ),
            )

            # dns setup for api
            await run_activity(
                activity=CreateCloudflareDNSRecordActivity,
                arg=CreateCloudflareDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{zsegment_config.domain_name}",
                    zone_id=zsegment_config.zone_id,
                    content=config.k8s_cname,
                ),
            )

            # dns setup for code server
            await run_activity(
                activity=CreateCloudflareDNSRecordActivity,
                arg=CreateCloudflareDNSRecordActivityModel(
                    domain_name=f"{tenant}.cs.{zsegment_config.domain_name}",
                    zone_id=zsegment_config.zone_id,
                    content=config.k8s_cname,
                ),
            )

            # create bucket
            bucket_name = f"{tenant}-{zsegment_config.domain_name.replace('.', '-')}"
            await run_activity(
                activity=CreateCloudflareBucketActivity,
                arg=CreateCloudflareBucketActivityModel(bucket_name=bucket_name),
            )

            # link bucket to custom domain
            await run_activity(
                activity=LinkBucketToDomainActivity,
                arg=LinkBucketToDomainActivityModel(
                    bucket_name=bucket_name,
                    domain_name=f"{tenant}.{zsegment_config.domain_name}",
                    zone_id=zsegment_config.zone_id,
                ),
            )

            # propagate the dns record
            await run_activity(
                activity=PropagateDNSRecordActivity,
                arg=PropagateDNSRecordActivityModel(
                    domain_name=f"{tenant}.api.{zsegment_config.domain_name}",
                ),
            )

            # ui setup
            repo_name = "zsegment-web"
            image_tag = "production" if config.env == "production" else "sprint"

            if config.env == "production":
                dest_dir = f"{bucket_name}/"
            else:
                dest_dir = f"{bucket_name}/{image_tag}"

            src_object_name = f"{repo_name}/{image_tag}/dist.zip"

            bundle_path = "bundle/dist"

            # copy artifacts to bucket
            await run_activity(
                activity=CopyArtifactsToBucketActivity,
                arg=CopyArtifactsToBucketActivityModel(
                    bucket_name=bucket_name,
                    src_object_name=src_object_name,
                    dest_dir=dest_dir,
                    bundle_path=bundle_path,
                    bundle_name="bundle.zip",
                    tenant=tenant,
                ),
            )

            # docs
            docs_dest_dir = f"{bucket_name}/docs"
            docs_src_object_name = f"{repo_name}/docs/dist.zip"

            docs_bundle_path = "bundle/dist"
            await run_activity(
                activity=CopyArtifactsToBucketActivity,
                arg=CopyArtifactsToBucketActivityModel(
                    bucket_name=bucket_name,
                    src_object_name=docs_src_object_name,
                    dest_dir=docs_dest_dir,
                    bundle_path=docs_bundle_path,
                    bundle_name="dist.zip",
                    tenant=tenant,
                ),
            )

            # statefulset pod creation for server
            await run_activity(  # yha htao
                activity=KubernetesDeploymentActivity,
                arg=KubernetesDeploymentActivityModel(
                    namespace=tenant,
                    name="zsegment-api",
                    docker_image=api_docker_image,
                    request_resource={
                        "cpu": pydash.get(zsegment, "serverSpec.request_cpu"),
                        "memory": pydash.get(zsegment, "serverSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(zsegment, "serverSpec.limit_cpu"),
                        "memory": pydash.get(zsegment, "serverSpec.limit_memory"),
                    },
                    container_ports={"http": 8090},
                    volume_mounts=[
                        {
                            "name": "tenant-volume",
                            "mount_path": f"/{config_dir}/{api_config}",
                            "sub_path": api_config,
                        },
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "zsegment-api-config",
                            "key": api_config,
                            "path": api_config,
                        }
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "WEB_CONCURRENCY", "value": "5"},
                        {"name": "CLIENT_CODE", "value": tenant},
                        {
                            "name": "SPRING_APPLICATION_JSON",
                            "value_from": {
                                "config_map_key_ref": {
                                    "name": "zsegment-api-config",
                                    "key": "api-config.json",
                                }
                            },
                        },
                        {"name": "POSTGRES_PASSWORD", "value": postgres_password},
                        {"name": "POSTGRES_USER", "value": postgres_username},
                        {"name": "EXTRACTOR_ENABLED", "value": "FALSE"},
                        {"name": "DYNAMIC_URL_ENABLED", "value": "True"},
                    ],
                ),
            )

            await run_activity(
                activity=KubernetesDeploymentActivity,
                arg=KubernetesDeploymentActivityModel(
                    namespace=tenant,
                    name="zsegment-engine",
                    docker_image=engine_docker_image,
                    request_resource={
                        "cpu": pydash.get(zsegment, "serverSpec.request_cpu"),
                        "memory": pydash.get(zsegment, "serverSpec.request_memory"),
                    },
                    limit_resource={
                        "cpu": pydash.get(zsegment, "serverSpec.limit_cpu"),
                        "memory": pydash.get(zsegment, "serverSpec.limit_memory"),
                    },
                    container_ports={"http": 8089},
                    volume_mounts=[
                        {
                            "name": "tenant-volume",
                            "mount_path": f"/{config_dir}/{engine_config}",
                            "sub_path": engine_config,
                        },
                    ],
                    volumes=[
                        {
                            "name": "tenant-volume",
                            "config_map_name": "zsegment-engine-config",
                            "key": engine_config,
                            "path": engine_config,
                        }
                    ],
                    container_envs=[
                        {"name": "DEPLOYMENT", "value": config.env},
                        {"name": "WEB_CONCURRENCY", "value": "5"},
                        {"name": "CLIENT_CODE", "value": tenant},
                        {
                            "name": "SPRING_APPLICATION_JSON",
                            "value_from": {
                                "config_map_key_ref": {
                                    "name": "zsegment-engine-config",
                                    "key": "engine-config.json",
                                }
                            },
                        },
                        {"name": "POSTGRES_PASSWORD", "value": postgres_password},
                        {"name": "POSTGRES_USER", "value": postgres_username},
                        {"name": "EXTRACTOR_ENABLED", "value": "FALSE"},
                        {"name": "DYNAMIC_URL_ENABLED", "value": "True"},
                    ],
                ),
            )

            # create droplet
            # template = template_env.get_template("dropletInitScript.sh")
            # init_script = template.render(debUrl=zsegment_config.deb_url)
            # ip_address: str = await run_activity(
            #     activity=CreateDropletActivity,
            #     arg=CreateDropletActivityModel(
            #         name=tenant,
            #         product=ProductName,
            #         script=init_script,
            #     ),
            # )

            # # setup dns
            # await run_activity(
            #     activity=CreateCloudflareDNSRecordActivity,
            #     arg=CreateCloudflareDNSRecordActivityModel(
            #         domain_name=f"{tenant}.droplet.{zsegment_config.domain_name}",
            #         zone_id=zsegment_config.zone_id,
            #         content=ip_address,
            #     ),
            # )

            # vm pod scraper
            await run_activity(
                activity=VMPodScrapperActivity,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="zsegment-api-metrics",
                    app="zsegment-api",
                    path="/api/v1/actuator/prometheus",
                    interval="5s",
                ),
            )

            await run_activity(
                activity=VMPodScrapperActivity,
                arg=VMPodScrapperActivityModel(
                    namespace=tenant,
                    name="zsegment-engine-metrics",
                    app="zsegment-engine",
                    path="/api/v1/actuator/prometheus",
                    interval="5s",
                ),
            )

            # kubernetes service
            # For Dev
            await run_activity(
                activity=KubernetesServiceActivity,
                arg=KubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="zsegment-api",
                    ports={"http": 8090, "grpc": 6565},
                ),
            )

            await run_activity(
                activity=KubernetesServiceActivity,
                arg=KubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="zsegment-engine",
                    ports={"http": 8089},
                ),
            )

            await run_activity(
                activity=KubernetesServiceActivity,
                arg=KubernetesServiceActivityModel(
                    namespace=tenant,
                    service_name="zsegment-api-grpc-nodeport",
                    selector="zsegment-api",
                    ports={"grpc": 6565},
                ),
            )

            # For Prod
            # await run_activity(
            #     activity=KubernetesServiceActivity,
            #     arg=KubernetesServiceActivityModel(
            #         namespace=tenant,
            #         service_name="zsegment-api-prod",
            #         ports={"http": 8090, "grpc": 6565},
            #     ),
            # )

            # await run_activity(
            #     activity=KubernetesServiceActivity,
            #     arg=KubernetesServiceActivityModel(
            #         namespace=tenant,
            #         service_name="zsegment-engine-prod",
            #         ports={"http": 8089},
            #     ),
            # )

            # await run_activity(
            #     activity=KubernetesServiceActivity,
            #     arg=KubernetesServiceActivityModel(
            #         namespace=tenant,
            #         service_name="zsegment-api-prod-grpc-nodeport",
            #         selector="zsegment-api-prod",
            #         ports={"grpc": 6565},
            #     ),
            # )

            # VS for dev
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
            await run_activity(
                activity=KubernetesIstioVirtualServiceActivity,
                arg=KubernetesIstioVirtualServiceActivityModel(
                    namespace=tenant,
                    host=f"{tenant}.api.{zsegment_config.domain_name}",
                    service_name="zsegment-api-vs",
                    payload=http_list,
                ),
            )

            await run_activity(
                activity=CreateKubernetesResourcesActivity,
                arg=CreateKubernetesResourcesActivityModel(namespace=tenant),
            )

            # check pod running status
            for pod in ["zsegment-api", "zsegment-engine"]:
                await run_activity(
                    activity=CheckPodRunningStatusActivity,
                    arg=CheckPodRunningStatusActivityModel(
                        namespace=tenant,
                        name=pod,
                    ),
                )

            grafana_template_path = os.path.join(TemplatePath, "grafana_dashboard_spring.json")

            await run_activity(
                activity=GrafanaDashboardActivity,
                arg=GrafanaDashboardProperties(
                    tenant=tenant,
                    grafana_url=zsegment_config.grafana_api_url,
                    api_key=zsegment_config.grafana_api_key,
                    template_path=grafana_template_path,
                ),
            )
            grafana_template_path = os.path.join(TemplatePath, "grafana_dashboard_camel.json")

            await run_activity(
                activity=GrafanaDashboardActivity,
                arg=GrafanaDashboardProperties(
                    tenant=tenant,
                    grafana_url=zsegment_config.grafana_api_url,
                    api_key=zsegment_config.grafana_api_key,
                    template_path=grafana_template_path,
                ),
            )
            # update tenant status
            await run_activity(
                activity=UpdateTenantStatusActivity,
                arg=TenantCliStatus(
                    tenant_name=tenant, status=TenantStatusEnum.Provisioned, product=ProductEnum.zsegment
                ),
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
                    domain_name=zsegment_config.domain_name,
                    product=ProductName,
                    from_name=zsegment_config.sender_name,
                    email_from=zsegment_config.sender_email,
                ),
            )

        except Exception as e:
            workflow.logger.error(f"Error in onboarding workflow: {e}")
            await run_activity(
                activity=UpdateTenantStatusActivity,
                arg=TenantCliStatus(
                    tenant_name=tenant,
                    status=TenantStatusEnum.ProvisioningFailed,
                    error_msg=str(e),
                    product=ProductEnum.zsegment,
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
