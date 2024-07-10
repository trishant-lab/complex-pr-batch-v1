from tempfile import TemporaryDirectory
from typing import Final

import boto3
from app.cli.temporal.core.log import log_info
from kubernetes.client import V1ConfigMap, V1ObjectMeta
from kubernetes.dynamic.exceptions import NotFoundError

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.dexit.dexit import DexitSpec
from app.core.settings import get_settings, AppSettings
from app.onepasswordutil import secret_inject
from app.s3_utils import download_file_from_storage, get_storage_client
from app.template_env import get_env
from loguru import logger


class ConfigMapClass(K8sResourceBaseClass):
    TENANT_CONFIG: Final[dict[str, str]] = {
        "name": "dexit-tenant-config",
        "key": "tenant-config.json",
    }
    ENV_CONFIG: Final[dict[str, str]] = {"name": "dexit-env-config", "key": "env-config.json"}
    VECTOR_CONFIG: Final[dict[str, str]] = {"name": "dexit-cli-vector-config", "key": "vector-config.toml"}

    def __init__(self: "ConfigMapClass", dexit: DexitSpec, config_map: dict[str, str]) -> None:
        """
        Initialize ConfigMapClass
        """
        self.dexit: DexitSpec = dexit
        self.config: AppSettings = get_settings()
        self.config_map: dict[str, str] = config_map
        self.env: str = get_settings().env
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.ConfigMap, api_version="v1"
        )

    def payload(self: "ConfigMapClass") -> dict:
        """
        Payload
        """
        template_file_name = (
            f"{self.env}-{self.config_map['key'].replace('.json', '.tmpl.json').replace('.toml', '.tmpl.toml')}"
        )

        config: AppSettings = get_settings()
        with TemporaryDirectory() as temp_dir:
            s3_client: boto3.client = get_storage_client(
                config=config, access_key=config.s3.access_key, secret_key=config.s3.secret_key
            )
            download_file_from_storage(
                object_name=f"{template_file_name}",
                file_path=f"{temp_dir}/{template_file_name}",
                storage_client=s3_client,
                bucket_name="dexit-config",
            )

            template_env = get_env(template_path=temp_dir)

            template = template_env.get_template(template_file_name)
            output = template.render(
                tenant=self.dexit.tenant,
                # customerId=self.dexit.customerDetails.customerId,
                # orgName=self.dexit.customerDetails.orgName,
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
                metadata=V1ObjectMeta(name=self.config_map["name"], namespace=self.dexit.tenant),
                data={self.config_map["key"]: open(f"{temp_dir}/{self.config_map['key']}").read()},
            )

            return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

    def put(self: "ConfigMapClass") -> None:
        """
        Put ConfigMapClass
        """
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource, body=self.payload(), field_manager="kubectl-client-side-apply"
        )
        log_info(message=f"{self.config_map['name']} created in namespace {self.dexit.tenant}")

    def delete(self: "ConfigMapClass") -> None:
        """
        Delete ConfigMapClass
        """
        try:
            self.k8s_dynamic_client.delete(
                resource=self.resource, name=self.config_map["name"], namespace=self.dexit.tenant
            )
        except NotFoundError:
            logger.error(f"ConfigMap {self.config_map['name']} not found in namespace {self.dexit.tenant}")
