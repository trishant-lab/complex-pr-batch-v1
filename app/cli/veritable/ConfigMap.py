from tempfile import TemporaryDirectory
from typing import Final

from kubernetes.client import V1ConfigMap, V1ObjectMeta
from kubernetes.dynamic.exceptions import NotFoundError
from loguru import logger

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.veritable.models.configmap import TenantMapClass, ProvisionMapClass, EnvMapClass, VectorMapClass
from app.cli.veritable.models.veritableSpec import VeritableSpec
from app.core.settings import get_settings, AppSettings
from app.onepasswordutil import secret_inject
from app.s3_utils import download_file_from_storage
from app.template_env import get_env


class ConfigMap(K8sResourceBaseClass):
    TENANT_CONFIG: Final[dict[str, str]] = {"name": TenantMapClass.name, "key": TenantMapClass.key}
    PROVISION_CONFIG: Final[dict[str, str]] = {"name": ProvisionMapClass.name, "key": ProvisionMapClass.key}
    ENV_CONFIG: Final[dict[str, str]] = {"name": EnvMapClass.name, "key": EnvMapClass.key}
    VECTOR_CONFIG: Final[dict[str, str]] = {"name": VectorMapClass.name, "key": VectorMapClass.key}

    def __init__(self: "ConfigMap", veritable: VeritableSpec, config_map: dict[str, str]) -> None:
        """
        Initialize the ConfigMap class
        """
        self.veritable: VeritableSpec = veritable
        self.config: AppSettings = get_settings()
        self.config_map: dict[str, str] = config_map
        self.env: str = get_settings().env
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.ConfigMap, api_version="v1"
        )

    def payload(self: "ConfigMap") -> dict:
        """
        Create a payload for the configmap
        """
        template_file_name = (
            f"{self.env}-{self.config_map['key'].replace('.json', '.tmpl.json').replace('.toml', '.tmpl.toml')}"
        )

        with TemporaryDirectory() as temp_dir:
            download_file_from_storage(
                object_name=f"new/{template_file_name}",
                file_path=f"{temp_dir}/{template_file_name}",
                config=self.config,
                bucket_name="veritable-config",
            )

            template_env = get_env(template_path=temp_dir)

            template = template_env.get_template(template_file_name)
            output = template.render(
                tenant=self.veritable.tenant,
                customerId=self.veritable.customerDetails.customerId,
                orgName=self.veritable.customerDetails.organization,
            )

            with open(f"{temp_dir}/{template_file_name}", "w") as f:
                f.write(output)

            # inject secret into tenant-config.json from 1Password
            secret_inject(
                source_file_path=f"{temp_dir}/{template_file_name}",
                destination_path=f"{temp_dir}/{self.config_map['key']}",
            )

            body = V1ConfigMap(
                api_version="v1",
                kind=ResourceKindEnum.ConfigMap.value,
                metadata=V1ObjectMeta(name=self.config_map["name"], namespace=self.veritable.tenant),
                data={self.config_map["key"]: open(f"{temp_dir}/{self.config_map['key']}").read()},
            )

            return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

    def put(self: "ConfigMap") -> None:
        """
        Create a configmap in the namespace
        """
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource, body=self.payload(), field_manager="kubectl-client-side-apply"
        )

    def delete(self: "ConfigMap") -> None:
        """
        Delete the configmap from the namespace
        """
        try:
            self.k8s_dynamic_client.delete(
                resource=self.resource, name=self.config_map["name"], namespace=self.veritable.tenant
            )
        except NotFoundError:
            logger.error(f"ConfigMap {self.config_map['name']} not found in namespace {self.veritable.tenant}")
