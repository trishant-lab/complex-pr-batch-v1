from tempfile import TemporaryDirectory
from typing import Final

from kubernetes.client import V1ConfigMap, V1ObjectMeta
from kubernetes.dynamic.exceptions import NotFoundError
from loguru import logger

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.penknife import TemplatePath
from app.cli.penknife.models.penknifespec import PenknifeSpec
from app.cli.temporal.core.log import log_info
from app.core.settings import get_settings
from app.onepasswordutil import secret_inject
from app.template_env import get_env


class ConfigMapClass(K8sResourceBaseClass):
    TENANT_CONFIG: Final[dict[str, str]] = {
        "name": "penknife-tenant-config",
        "key": "tenant-config.json",
    }
    VECTOR_CONFIG: Final[dict[str, str]] = {"name": "penknife-cli-vector-config", "key": "vector-config.toml"}
    STATE_STORE_CONFIG: Final[dict[str, str]] = {"name": "penknife-statestore-config", "key": "statestore.yaml"}

    def __init__(self: "ConfigMapClass", penknife: PenknifeSpec, config_map: dict[str, str]) -> None:
        """
        Constructor for ConfigMapClass
        """
        self.penknife: PenknifeSpec = penknife
        self.config_map: dict[str, str] = config_map
        self.config_ = get_settings()
        self.env: str = self.config_.env
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.ConfigMap, api_version="v1"
        )

    def payload(self: "ConfigMapClass") -> dict:
        """
        Payload for ConfigMap
        """
        template_env = get_env(template_path=TemplatePath)

        template_file_name = f"""{self.env}-{self.config_map['key']
            .replace('.json', '.tmpl.json')
            .replace('.toml', '.tmpl.toml')
            .replace('.yaml', '.tmpl.yaml')
            .replace('.conf', '.tmpl.conf')}"""

        template = template_env.get_template(template_file_name)
        output = template.render(
            tenant=self.penknife.tenant,
            redis_admin_password=self.config_.cache_admin_password,
        )

        with TemporaryDirectory() as temp_dir:
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
                metadata=V1ObjectMeta(name=self.config_map["name"], namespace=self.penknife.tenant),
                data={self.config_map["key"]: open(f"{temp_dir}/{self.config_map['key']}").read()},
            )

            return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

    def put(self: "ConfigMapClass") -> None:
        """
        Put ConfigMap
        """
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource, body=self.payload(), field_manager="kubectl-client-side-apply"
        )
        log_info(f"ConfigMap {self.config_map['name']} created successfully.")

    def delete(self: "ConfigMapClass") -> None:
        """
        Delete ConfigMap
        """
        try:
            self.k8s_dynamic_client.delete(
                resource=self.resource, name=self.config_map["name"], namespace=self.penknife.tenant
            )
        except NotFoundError:
            logger.error(f"ConfigMap {self.config_map['name']} not found in namespace {self.penknife.tenant}")
