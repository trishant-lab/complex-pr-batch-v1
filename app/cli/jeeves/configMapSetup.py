from tempfile import TemporaryDirectory
from typing import Final

from kubernetes.client import V1ConfigMap, V1ObjectMeta
from kubernetes.dynamic.exceptions import NotFoundError
from loguru import logger

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.jeeves import TemplatePath
from app.cli.jeeves.common import JeevesSpec
from app.core.settings import get_settings
from app.onepasswordutil import secret_inject
from app.template_env import get_env


class ConfigMapClass(K8sResourceBaseClass):
    TENANT_CONFIG: Final[dict[str, str]] = {
        "name": "jeeves-tenant-config",
        "key": "tenant-config.json",
    }
    RCLONE_CONFIG: Final[dict[str, str]] = {
        "name": "jeeves-rclone-config",
        "key": "rclone.conf",
    }
    VECTOR_CONFIG: Final[dict[str, str]] = {
        "name": "jeeves-cli-vector-config",
        "key": "vector-config.toml"
    }
    STATE_STORE_CONFIG: Final[dict[str, str]] = {
        "name": "jeeves-statestore-config",
        "key": "statestore.yaml"
    }

    def __init__(self, jeeves: JeevesSpec, config_map: dict[str, str]) -> None:
        self.jeeves: JeevesSpec = jeeves
        self.config_map: dict[str, str] = config_map
        self.config_ = get_settings()
        self.env: str = self.config_.env
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.ConfigMap, api_version="v1"
        )

    def payload(self):
        template_env = get_env(template_path=TemplatePath)

        template_file_name = (
            f"""{self.env}-{self.config_map['key']
            .replace('.json', '.tmpl.json')
            .replace('.toml', '.tmpl.toml')
            .replace('.yaml', '.tmpl.yaml')
            .replace('.conf', '.tmpl.conf')}"""
        )

        template = template_env.get_template(template_file_name)
        output = template.render(
            tenant=self.jeeves.tenant,
            redis_admin_password=self.config_.cache_admin_password,
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
                metadata=V1ObjectMeta(name=self.config_map['name'], namespace=self.jeeves.tenant),
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
                namespace=self.jeeves.tenant
            )
        except NotFoundError:
            logger.error(f"ConfigMap {self.config_map['name']} not found in namespace {self.jeeves.tenant}")
