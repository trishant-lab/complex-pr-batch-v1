from enum import Enum
from functools import lru_cache

from kubernetes import client as api_client, config as k8s_config
from kubernetes.dynamic import DynamicClient, Resource


class ResourceKindEnum(Enum):
    """
    Enum for k8s resource kind
    """

    Namespace = "Namespace"
    Service = "Service"
    ConfigMap = "ConfigMap"
    Secret = "Secret"
    Job = "Job"
    Pod = "Pod"
    Deployment = "Deployment"
    VirtualService = "VirtualService"
    PersistentVolumeClaim = "PersistentVolumeClaim"
    PersistentVolume = "PersistentVolume"
    VMPodScrape = "VMPodScrape"
    StatefulSet = "StatefulSet"
    VeritableTenant = "VeritableTenant"
    PractiflyTenant = "PractiflyTenant"


@lru_cache
def get_dynamic_client() -> DynamicClient:
    """
    Get k8s dynamic client
    """
    k8s_api_client = api_client.ApiClient(configuration=k8s_config.load_kube_config())
    return DynamicClient(k8s_api_client)


@lru_cache
def get_custom_objects_api() -> api_client.CustomObjectsApi:
    """
    Get k8s custom objects api
    """
    k8s_api_client = api_client.ApiClient(configuration=k8s_config.load_kube_config())
    return api_client.CustomObjectsApi(api_client=k8s_api_client)


def get_resource(dynamic_client: DynamicClient, kind: ResourceKindEnum, api_version: str) -> Resource:
    """
    Get k8s resource object
    """
    return dynamic_client.resources.get(kind=kind.value, api_version=api_version)
