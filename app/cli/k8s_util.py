from enum import Enum

from kubernetes import client as api_client, config as k8s_config
from kubernetes.dynamic import DynamicClient, Resource


class ResourceKindEnum(Enum):
    Namespace = "Namespace"
    Service = "Service"
    ConfigMap = "ConfigMap"
    Secret = "Secret"
    Job = "Job"
    Pod = "Pod"
    Deployment = "Deployment"
    VirtualService = "VirtualService"
    PersistentVolumeClaim = "PersistentVolumeClaim"
    VMPodScrape = "VMPodScrape"


def get_dynamic_client() -> DynamicClient:
    k8s_api_client = api_client.ApiClient(configuration=k8s_config.load_kube_config())
    dynamic_client = DynamicClient(k8s_api_client)
    return dynamic_client


def get_resource(dynamic_client: DynamicClient, kind: ResourceKindEnum, api_version: str) -> Resource:
    return dynamic_client.resources.get(
        kind=kind.value,
        api_version=api_version
    )
