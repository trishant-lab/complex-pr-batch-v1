from dataclasses import dataclass
from uuid import UUID

from app.cli.temporal.core.base import IODataclass

ProductName: str = "veritable"
OnepasswordVaultName: str = "practifly"
OnepasswordItemName: str = "veritable-tenant-config-{environment}"


@dataclass
class ResourceSpec:
    """
    ResourceSpec dataclass
    """
    request_memory: str
    request_cpu: str
    limit_memory: str
    limit_cpu: str


@dataclass
class VeritableSpec(IODataclass):
    """
    VeritableSpec dataclass
    """
    tenant: str
    imageTag: None | str = None
    customerId: None | UUID = None
    customerUserName: None | str = None
    customerEmail: None | str = None
    customerRealmRoles: None | list[str] = None
    orgName: None | str = None
    serverSpec: None | ResourceSpec = None
    cliSpec: None | ResourceSpec = None


# ConfigMapBaseClass to be used as base class for all ConfigMap enums


class VectorConfigMap:
    """
    VeritableVectorConfigMap Enum
    """
    name = "veritable-cli-vector-config"
    key = "vector-config.toml"


class EnvConfigMap:
    """
    VeritableEnvConfigMap Enum
    """
    name = "veritable-env-config"
    key = "env-config.json"


class ProvisioningConfigMap:
    """
    VeritableProvisioningConfigMap Enum
    """
    name = "veritable-provisioning-config"
    key = "provisioning-config.json"


class TenantConfigMap:
    """
    VeritableTenantConfigMap Enum
    """
    name = "veritable-tenant-config"
    key = "tenant-config.json"
