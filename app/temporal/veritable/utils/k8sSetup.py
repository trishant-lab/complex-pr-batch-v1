from loguru import logger

from app.core.settings import AppSettings, get_settings
from app.temporal.common.kubernetesService import KubernetesService
from app.temporal.common.namespaceSetup import Namespace
from app.temporal.common.pvcSetup import PVC
from app.temporal.common.secrets import KubernetesSecretService
from app.temporal.veritable.utils.common import VeritableSpec, ProductName


async def create_namespace(veritable: VeritableSpec) -> None:
    """
    Create namespace in k8s
    :param veritable:
    :return:
    """
    namespace = Namespace(namespace=f"{veritable.tenant}")
    await namespace.create()
    logger.info(f"Created namespace for {veritable.tenant}")


async def create_pvc(veritable: VeritableSpec) -> None:
    """
    Create PVC in k8s
    :param veritable:
    :return:
    """
    namespace: str = veritable.tenant
    pvc = PVC(namespace=namespace, pvc_name=f"veritable-pvc")
    await pvc.create(storage="200Mi")
    logger.info(f"Created PVC for {veritable.tenant}")


async def create_secret_service(veritable: VeritableSpec) -> None:
    """
    Create secret in k8s
    :param veritable:
    :return:
    """
    config: AppSettings = get_settings()

    namespace: str = veritable.tenant
    secret_name: str = f"registrycred"
    data: dict = {
        ".dockerconfigjson": config.docker_image_pull_secret
    }
    secret = KubernetesSecretService(namespace, secret_name)

    await secret.create_or_replace(data)
    logger.info(f"Created secret for {veritable.tenant}")


async def create_k8s_service(veritable: VeritableSpec) -> None:
    """
    Setup k8s service
    :param veritable:
    :return:
    """
    k8s_service = KubernetesService(
        namespace=veritable.tenant,
        product_name=ProductName,
    )

    await k8s_service.create_or_replace(port=8000)
    logger.info(f"Created services for {veritable.tenant}")


