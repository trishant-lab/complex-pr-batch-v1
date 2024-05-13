from tempfile import TemporaryDirectory
from typing import Final

from kubernetes.client import V1ConfigMap, V1ObjectMeta
from kubernetes.dynamic.exceptions import NotFoundError
from loguru import logger

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.veritable import TemplatePath
from app.cli.veritable.common import VeritableSpec, TenantConfigMap, \
    ProvisioningConfigMap, EnvConfigMap, VectorConfigMap
from app.core.settings import AppSettings, get_settings
from app.onepasswordutil import secret_inject
from app.template_env import get_env


class ConfigMapClass(K8sResourceBaseClass):
    TENANT_CONFIG: Final[dict[str, str]] = {
        "name": "veritable-tenant-config",
        "key": "tenant-config.json",
    }
    PROVISION_CONFIG: Final[dict[str, str]] = {
        "name": "veritable-provisioning-config",
        "key": "provisioning-config.json"
    }
    ENV_CONFIG: Final[dict[str, str]] = {
        "name": "veritable-env-config",
        "key": "env-config.json"
    }
    VECTOR_CONFIG: Final[dict[str, str]] = {
        "name": "veritable-cli-vector-config",
        "key": "vector-config.toml"
    }

    def __init__(self, veritable: VeritableSpec, config_map: dict[str, str]) -> None:
        self.veritable: VeritableSpec = veritable
        self.config_map: dict[str, str] = config_map
        self.env: str = get_settings().env
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.ConfigMap, api_version="v1"
        )

    def payload(self):
        template_env = get_env(template_path=TemplatePath)

        template_file_name = (
            f"{self.env}-{self.config_map['key'].replace('.json', '.tmpl.json').replace('.toml', '.tmpl.toml')}"
        )

        template = template_env.get_template(template_file_name)  # todo get template from minio
        output = template.render(
            tenant=self.veritable.tenant,
            customerId=self.veritable.customerId,
            orgName=self.veritable.orgName,
        )

        with TemporaryDirectory() as temp_dir:
            with open(f"{temp_dir}/{template_file_name}", "w") as f:
                f.write(output)

            # inject secret into tenant-config.json from 1Password
            secret_inject(
                source_file_path=f"{temp_dir}/{template_file_name}",
                destination_path=f"{temp_dir}/{self.config_map['key']}"
            )

            body = V1ConfigMap(
                api_version="v1",
                kind=ResourceKindEnum.ConfigMap.value,
                metadata=V1ObjectMeta(name=self.config_map['name'], namespace=self.veritable.tenant),
                data={self.config_map['key']: open(f"{temp_dir}/{self.config_map['key']}").read()}
            )

            body = self.k8s_dynamic_client.client.sanitize_for_serialization(body)

            return body

    def put(self):
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource,
            body=self.payload(),
            field_manager="kubectl-client-side-apply"
        )

    def delete(self):
        try:
            self.k8s_dynamic_client.delete(
                resource=self.resource,
                name=self.config_map['name'],
                namespace=self.veritable.tenant
            )
        except NotFoundError as e:
            logger.error(f"ConfigMap {self.config_map['name']} not found in namespace {self.veritable.tenant}")