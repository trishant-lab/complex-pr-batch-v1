import dataclasses
from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity
from app.cli.jeeves.jeeves import JeevesSpec


# from app.models.tenant import TenantStatusEnum


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
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        from app.cli.jeeves.postgresSetup import setup_postgres
        await setup_postgres(
            jeeves=jeeves
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
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        # create namespace in k8s
        from app.cli.jeeves.namespaceSetup import Namespace
        Namespace(jeeves=jeeves).put()


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
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        from app.cli.jeeves.configMapSetup import ConfigMapClass
        ConfigMapClass(jeeves=jeeves, config_map=ConfigMapClass.TENANT_CONFIG).put()
        ConfigMapClass(jeeves=jeeves, config_map=ConfigMapClass.RCLONE_CONFIG).put()
        ConfigMapClass(jeeves=jeeves, config_map=ConfigMapClass.VECTOR_CONFIG).put()
        ConfigMapClass(jeeves=jeeves, config_map=ConfigMapClass.STATE_STORE_CONFIG).put()


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
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="pvc_setup_activity")
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        # create PVC in k8s for namespace
        from app.cli.jeeves.pvcSetup import PVC
        PVC(jeeves=jeeves).put()


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
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        # create secret in k8s for namespace
        from app.cli.jeeves.secretSetup import Secret
        from app.core.settings import get_settings, AppSettings

        config: AppSettings = get_settings()

        # Create registry secret for pulling images
        Secret(
            jeeves=jeeves,
            name="registrycred",
            type="kubernetes.io/dockerconfigjson",
            data={
                ".dockerconfigjson": config.docker_image_pull_secret
            }
        ).put()

        # Create redis secret for redis password
        Secret(
            jeeves=jeeves,
            name="cache-secret",
            data={
                "REDIS_PASSWORD": config.cache_admin_password
            }
        ).put()


class StateFullSetSetupActivity(Activity):
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
    @activity.defn(name="state_full_set_setup_activity")
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        # create stateful set in k8s
        from app.cli.jeeves.statefulSetup import StateFullSet
        await StateFullSet(jeeves=jeeves).put()


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
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        # Create DNS
        from app.cli.jeeves.dnsSetup import dns_setup
        await dns_setup(jeeves=jeeves)


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
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        # Deploy ui
        from app.cli.jeeves.UISetup import UISetup
        UISetup(jeeves=jeeves).deploy()


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
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        # Deploy keycloak
        from app.cli.jeeves.keycloakRealmSetup import create_realm_and_users
        await create_realm_and_users(jeeves=jeeves)


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
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        # Setup novu
        from app.cli.jeeves.novuSetup import NovuSetup
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
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="provisioning_job_activity")
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        # Check provisioning status
        from app.cli.jeeves.Job import AlembicJob, VespaJob
        alembic_job = AlembicJob(jeeves=jeeves)
        alembic_job.delete()
        alembic_job.put()

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
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="kubernetes_service_activity")
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        # Create k8s service
        from app.cli.jeeves.serviceSetup import Service
        Service(jeeves=jeeves).put()


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
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        # Create k8s virtual service
        from app.cli.jeeves.istioVitualService import IstioVirtualService
        IstioVirtualService(jeeves=jeeves).put()


class DeploymentActivity(Activity):
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
    @activity.defn(name="deployment_activity")
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        # Deploy k8s deployment
        from app.cli.jeeves.depolyment import DeploymentServer, DeploymentCli
        DeploymentServer(jeeves=jeeves).put()
        DeploymentCli(jeeves=jeeves).put()


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
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        # Scrape pod logs
        from app.cli.jeeves.vmPodScraper import VMPodScrapperServer
        VMPodScrapperServer(jeeves=jeeves).put()


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
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        # Todo: Implement this
        # Setup grafana alerts
        # from app.cli.jeeves.grafanaAlerts import create_grafana_alerts
        # await create_grafana_alerts(jeeves)


# @dataclasses.dataclass
# class TenantStatus:
#     """
#     TenantStatus dataclass
#     """
#     tenant_name: str
#     status: TenantStatusEnum
#     error_msg: None | str = None


# class UpdateTenantStatusActivity(Activity):
#     @staticmethod
#     def get_retry_policy() -> RetryPolicy:
#         """
#         RetryPolicy for the activity
#         """
#         return RetryPolicy(
#             initial_interval=timedelta(seconds=1),
#             backoff_coefficient=2,
#             maximum_interval=timedelta(seconds=10),
#             maximum_attempts=1,
#         )
#
#     @staticmethod
#     @activity.defn(name="UpdateTenantStatusActivity")
#     async def defn(activity_input: TenantStatus):
#         """
#         Callable for the activity
#         """
#         # Update tenant status
#         from app.cli.common.tenantStatus import update_tenant_status
#         from app.cli.jeeves.jeeves import ProductName
#         await update_tenant_status(
#             tenant_name=activity_input.tenant_name,
#             product=ProductName,
#             status=activity_input.status,
#             error_message=activity_input.error_msg
#         )


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
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="chatwoot_setup_activity")
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        # Setup chatwoot
        from app.cli.jeeves.chatwootSetup import ChatwootSetup
        ChatwootSetup(jeeves=jeeves).setup()


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
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        # Create temporal namespace
        from app.cli.jeeves.temporalNamespaceCreation import TemporalNamespaceCreation
        await TemporalNamespaceCreation(jeeves=jeeves).create_temporal_namespace()


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
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="ai_voice_setup_activity")
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        # Add AI voices to storage
        from app.cli.jeeves.aiVoiceSetup import add_ai_voices_to_storage
        add_ai_voices_to_storage(jeeves=jeeves)


class SlackNotification(Activity):
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
    @activity.defn(name="slack_notification_activity")
    async def defn(jeeves: JeevesSpec):
        """
        Callable for the activity
        """
        # Send Slack notification
        from app.slack_utils import send_slack_msg
        text = (
            f"A new Jeeves tenant has been requested by "
            f"{jeeves.customerDetails.email} from {jeeves.customerDetails.organization}"
        )
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text,
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Tenant:* {jeeves.tenant}",
                    }
                ],
            },
        ]
        send_slack_msg(text=text, blocks=blocks)
