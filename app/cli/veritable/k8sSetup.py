from kubernetes.client import (
    V1ObjectMeta, V1PersistentVolumeClaimSpec, V1ResourceRequirements, V1PersistentVolumeClaim, V1Namespace, V1Secret,
    V1Service, V1ManagedFieldsEntry, V1ServiceSpec, V1ServicePort
)
from loguru import logger

from app.cli.k8s_util import get_dynamic_client, ResourceKindEnum, get_resource
from app.cli.veritable.common import VeritableSpec, ProductName
from app.core.settings import AppSettings, get_settings


async def create_namespace(veritable: VeritableSpec) -> None:
    """
    Create namespace in k8s
    :param veritable:
    :return:
    """

    k8s_dynamic_client = get_dynamic_client()
    resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Namespace, api_version="v1")

    namespace_body = V1Namespace(
        api_version="v1",
        kind=ResourceKindEnum.Namespace.value,
        metadata=V1ObjectMeta(name=f"{veritable.tenant}")
    )

    namespace_body = k8s_dynamic_client.client.sanitize_for_serialization(namespace_body)

    k8s_dynamic_client.server_side_apply(
        resource,
        body=namespace_body,
        field_manager="kubectl-client-side-apply"
    )
    logger.info(f"Created namespace for {veritable.tenant}")


async def create_pvc(veritable: VeritableSpec) -> None:
    """
    Create PVC in k8s
    :param veritable:
    :return:
    """

    k8s_dynamic_client = get_dynamic_client()
    resource = get_resource(
        dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.PersistentVolumeClaim, api_version="v1"
    )

    pvc_body = V1PersistentVolumeClaim(
        api_version="v1",
        kind=ResourceKindEnum.PersistentVolumeClaim.value,
        metadata=V1ObjectMeta(
            namespace=veritable.tenant,
            name=f"veritable-pvc"
        ),
        spec=V1PersistentVolumeClaimSpec(
            volume_mode="Filesystem",
            storage_class_name="topolvm-provisioner",
            access_modes=["ReadWriteOnce"],
            resources=V1ResourceRequirements(
                requests={"storage": "200Mi"}
            ),
        ),
    )

    pvc_body = k8s_dynamic_client.client.sanitize_for_serialization(pvc_body)

    k8s_dynamic_client.server_side_apply(
        resource=resource,
        body=pvc_body,
        field_manager="kubectl-client-side-apply"
    )

    logger.info(f"Created PVC for {veritable.tenant}")


async def delete_pvc(tenant_name: str) -> None:
    """
    Delete PVC in k8s
    """

    k8s_dynamic_client = get_dynamic_client()
    resource = get_resource(
        dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.PersistentVolumeClaim, api_version="v1"
    )
    k8s_dynamic_client.delete(
        resource=resource,
        namespace=tenant_name,
        name="veritable-pvc"
    )


async def create_secret_service(veritable: VeritableSpec) -> None:
    """
    Create secret in k8s
    :param veritable:
    :return:
    """
    config: AppSettings = get_settings()

    k8s_dynamic_client = get_dynamic_client()
    resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Secret, api_version="v1")

    secret_body = V1Secret(
        api_version="v1",
        kind=ResourceKindEnum.Secret.value,
        metadata=V1ObjectMeta(
            namespace=veritable.tenant,
            name="registrycred"
        ),
        type="kubernetes.io/dockerconfigjson",
        data={
            ".dockerconfigjson": config.docker_image_pull_secret
        }
    )

    secret_body = k8s_dynamic_client.client.sanitize_for_serialization(secret_body)

    k8s_dynamic_client.server_side_apply(
        resource=resource,
        body=secret_body,
        field_manager="kubectl-client-side-apply"
    )

    logger.info(f"Created secret for {veritable.tenant}")


async def create_k8s_service(veritable: VeritableSpec) -> None:
    """
    Setup k8s service
    :param veritable:
    :return:
    """

    k8s_dynamic_client = get_dynamic_client()
    resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Service, api_version="v1")

    body = V1Service(
        api_version="v1",
        kind=ResourceKindEnum.Service.value,
        metadata=V1ObjectMeta(
            name=ProductName,
            namespace=veritable.tenant,
            labels={"app": ProductName},
        ),
        spec=V1ServiceSpec(
            selector={"app": ProductName},
            type="ClusterIP",
            ports=[
                V1ServicePort(
                    name="http",
                    port=8000,
                )
            ]
        )
    )

    body = k8s_dynamic_client.client.sanitize_for_serialization(body)

    k8s_dynamic_client.server_side_apply(
        resource=resource,
        body=body,
        field_manager="kubectl-client-side-apply"
    )

    logger.info(f"Created services for {veritable.tenant}")


async def delete_k8s_service(tenant_name: str) -> None:
    """
    Delete k8s service
    :param tenant_name:
    :return:
    """

    k8s_dynamic_client = get_dynamic_client()
    resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Service, api_version="v1")
    k8s_dynamic_client.delete(
        resource=resource,
        namespace=tenant_name,
        name=ProductName
    )
