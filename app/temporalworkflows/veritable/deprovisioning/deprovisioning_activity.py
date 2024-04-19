from temporalio import activity
from loguru import logger

from app.core.settings import AppSettings, get_settings, KeycloakSettings
from app.temporalworkflows.common.GoogleDNS import GoogleDNS
from app.temporalworkflows.common.configmap import ConfigMap
from app.temporalworkflows.common.deployment import DeploymentJob
from app.temporalworkflows.common.istio_virtual_service import IstioVirtualService
from app.temporalworkflows.common.keyclaokrealmsetup.keycloakutils import KeycloakAdminClient
from app.temporalworkflows.common.kubernetes_service import KubernetesService
from app.temporalworkflows.common.pvcsetup import PVC
from app.temporalworkflows.common.vmpodscrapper import VMPodScrapper


@activity.defn
async def delete_all_resources(tenant: str) -> None:
    """
    Deprovisioning activity
    """
    logger.info(f"Deprovisioning resources for tenant: {tenant}")

    config: AppSettings = get_settings()

    # Delete k8s service
    await KubernetesService(namespace=tenant, product_name="veritable").delete()

    # Delete istio virtual service
    await IstioVirtualService(namespace=tenant, product="veritable").delete()

    # Delete Server Deployment Job
    await DeploymentJob(namespace=tenant, deployment_name="veritable", product_name="veritable").delete()

    # Delete CLI Deployment Job
    await DeploymentJob(namespace=tenant, deployment_name="veritable-cli", product_name="veritable").delete()

    # Delete configmap
    await ConfigMap(namespace=tenant).delete_config(name="veritable-tenant-config")
    await ConfigMap(namespace=tenant).delete_config(name="veritable-provisioning-config")
    await ConfigMap(namespace=tenant).delete_config(name="veritable-env-config")
    await ConfigMap(namespace=tenant).delete_config(name="veritable-cli-vector-config")

    # Delete PVC
    await PVC(namespace=tenant, pvc_name="veritable-pvc").delete()

    # delete realm
    config: AppSettings = get_settings()
    keycloak_config: KeycloakSettings = config.keycloak
    keycloak_client = KeycloakAdminClient(keycloak_config)

    keycloak_client.delete_realm(f"veritable_{tenant}")

    # delete dns
    domain_name: str = config.product_config.get("veritable").domain_name
    GoogleDNS(
        cname=f"{config.google_dns_cname}.",
        fqdn=f"{tenant}.{domain_name}.",
        zone_name="veritableapp"
    ).delete()
    logger.info(f"Deleted DNS record for {tenant}.{domain_name}")

    # delete server vm pod scrapper
    await VMPodScrapper(namespace=tenant, name="veritable-metrics").delete()

    # delete cli vm pod scrapper
    await VMPodScrapper(namespace=tenant, name="veritable-cli-metrics").delete()

    # todo delete grafana alerts
