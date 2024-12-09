from kubernetes.client import V1ObjectMeta, V1PersistentVolumeClaim, V1PersistentVolumeClaimSpec, V1ResourceRequirements
from temporalio import activity, workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from datetime import timedelta
    from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
    from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
    from app.cli.temporal.core.log import log_info
    from app.core.settings import AppSettings, get_settings


class PVCSetupActivityModel(LaunchpadCLIBaseModel):
    """
    Model for PVCSetupActivity
    """

    tenant: str
    pvc_name: str


class PVCSetupActivity(Activity):
    """
    Activity to setup PVC
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=60)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=60),
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="PVCSetupActivity")
    async def defn(activity_model: PVCSetupActivityModel) -> None:
        """
        Activity definition
        """
        config: AppSettings = get_settings()

        k8s_dynamic_client = get_dynamic_client()
        pvc_resource = get_resource(
            dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.PersistentVolumeClaim, api_version="v1"
        )

        body = V1PersistentVolumeClaim(
            api_version="v1",
            kind=ResourceKindEnum.PersistentVolumeClaim.value,
            metadata=V1ObjectMeta(namespace=activity_model.tenant, name=activity_model.pvc_name),
            spec=V1PersistentVolumeClaimSpec(
                volume_mode="Filesystem",
                storage_class_name="longhorn-replicated" if config.env == "integration" else "topolvm-provisioner",
                access_modes=["ReadWriteOnce"],
                resources=V1ResourceRequirements(requests={"storage": "1Gi"}),
            ),
        )

        payload = k8s_dynamic_client.client.sanitize_for_serialization(body)
        k8s_dynamic_client.server_side_apply(
            resource=pvc_resource, body=payload, field_manager="kubectl-client-side-apply"
        )

        log_info(f"PVC {activity_model.pvc_name} created successfully")


class PVCDeletionActivityModel(LaunchpadCLIBaseModel):
    """
    Model for PVCDeletionActivity
    """

    tenant: str
    pvc_name: str


class PVCDeletionActivity(Activity):
    """
    Activity to delete PVC
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=60)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5, backoff_coefficient=2)

    @staticmethod
    @activity.defn(name="PVCDeletionActivity")
    async def defn(activity_model: PVCDeletionActivityModel) -> None:
        """
        Activity definition
        """
        k8s_dynamic_client = get_dynamic_client()
        pvc_resource = get_resource(
            dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.PersistentVolumeClaim, api_version="v1"
        )

        k8s_dynamic_client.delete(resource=pvc_resource, name=activity_model.pvc_name, namespace=activity_model.tenant)
