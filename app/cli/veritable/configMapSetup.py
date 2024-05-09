import os
from tempfile import TemporaryDirectory

from cryptography.fernet import Fernet
from kubernetes.client import V1ConfigMap, V1ObjectMeta

from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.veritable import TemplatePath
from app.cli.veritable.common import VeritableSpec, OnepasswordVaultName, ProductName, TenantConfigMap, \
    ProvisioningConfigMap, EnvConfigMap, VectorConfigMap
from app.onepasswordutil import OnePasswordUtil, secret_inject
from app.template_env import get_env


def apply_tenant_config(veritable: VeritableSpec):
    """
    :return:
    """
    environment: str = os.getenv("DEPLOYMENT", "integration").lower()
    template_env = get_env(template_path=TemplatePath)
    template = template_env.get_template(f"{environment}-tenant-config.tmpl.json")
    output = template.render(
        tenant=veritable.tenant,
    )

    with TemporaryDirectory() as temp_dir:
        with open(f"{temp_dir}/{environment}-tenant-config.tmpl.json", "w") as f:
            f.write(output)

        # inject secret into tenant-config.json from 1Password
        secret_inject(
            source_file_path=f"{temp_dir}/{environment}-tenant-config.tmpl.json",
            destination_path=f"{temp_dir}/tenant-config.json"
        )

        k8s_dynamic_client = get_dynamic_client()
        resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.ConfigMap, api_version="v1")

        body = V1ConfigMap(
            api_version="v1",
            kind="ConfigMap",
            metadata=V1ObjectMeta(name=TenantConfigMap.name, namespace=veritable.tenant),
            data={TenantConfigMap.key: open(f"{temp_dir}/tenant-config.json").read()}
        )

        body = k8s_dynamic_client.client.sanitize_for_serialization(body)

        k8s_dynamic_client.server_side_apply(
            resource=resource,
            body=body,
            field_manager="kubectl-client-side-apply"
        )


def apply_provisioning_config(veritable: VeritableSpec):
    """
    :return:
    """
    environment: str = os.getenv("DEPLOYMENT", "integration").lower()
    template_env = get_env(template_path=TemplatePath)
    template = template_env.get_template(f"{environment}-provisioning-config.tmpl.json")
    output = template.render(
        tenant=veritable.tenant,
        customerId=veritable.customerId,
        orgName=veritable.orgName,
    )

    with TemporaryDirectory() as temp_dir:
        with open(f"{temp_dir}/{environment}-provisioning-config.tmpl.json", "w") as f:
            f.write(output)

        # inject secret into tenant-config.json from 1Password
        secret_inject(
            source_file_path=f"{temp_dir}/{environment}-provisioning-config.tmpl.json",
            destination_path=f"{temp_dir}/provisioning-config.json"
        )

        k8s_dynamic_client = get_dynamic_client()
        resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.ConfigMap, api_version="v1")

        body = V1ConfigMap(
            api_version="v1",
            kind="ConfigMap",
            metadata=V1ObjectMeta(name=ProvisioningConfigMap.name, namespace=veritable.tenant),
            data={ProvisioningConfigMap.key: open(f"{temp_dir}/provisioning-config.json").read()}
        )
        body = k8s_dynamic_client.client.sanitize_for_serialization(body)

        k8s_dynamic_client.server_side_apply(
            resource=resource,
            body=body,
            field_manager="kubectl-client-side-apply"
        )


def apply_env_config(veritable: VeritableSpec):
    """
    :return:
    """
    environment: str = os.getenv("DEPLOYMENT", "integration").lower()
    template_env = get_env(template_path=TemplatePath)
    template = template_env.get_template(f"{environment}-env-config.tmpl.json")
    output = template.render(
        tenant=veritable.tenant,
    )

    with TemporaryDirectory() as temp_dir:
        with open(f"{temp_dir}/{environment}-env-config.tmpl.json", "w") as f:
            f.write(output)

        # inject secret into tenant-config.json from 1Password
        secret_inject(
            source_file_path=f"{temp_dir}/{environment}-env-config.tmpl.json",
            destination_path=f"{temp_dir}/env-config.json"
        )

        k8s_dynamic_client = get_dynamic_client()
        resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.ConfigMap, api_version="v1")

        body = V1ConfigMap(
            api_version="v1",
            kind=ResourceKindEnum.ConfigMap.value,
            metadata=V1ObjectMeta(name=EnvConfigMap.name, namespace=veritable.tenant),
            data={EnvConfigMap.key: open(f"{temp_dir}/env-config.json").read()}
        )
        body = k8s_dynamic_client.client.sanitize_for_serialization(body)

        k8s_dynamic_client.server_side_apply(
            resource=resource,
            body=body,
            field_manager="kubectl-client-side-apply"
        )


def apply_vector_config(veritable: VeritableSpec):
    """
    :return:

    """
    k8s_dynamic_client = get_dynamic_client()
    resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.ConfigMap, api_version="v1")

    body = V1ConfigMap(
        api_version="v1",
        kind=ResourceKindEnum.ConfigMap.value,
        metadata=V1ObjectMeta(name=VectorConfigMap.name, namespace=veritable.tenant),
        data={
            VectorConfigMap.key: "[log_schema]\nhost_key = \"host\"\nmessage_key = \"message\"\nsource_type_key = \"source_type\"\ntimestamp_key = \"timestamp\"\n\n# sources for logs\n\n[sources.custom_logs]\ntype = \"file\"\ninclude = [\"/var/log/supervisord/veritable_*\"]\nfingerprint.strategy = \"device_and_inode\"\n\n[sinks.vector_sink]\ntype = \"loki\"\ninputs = [ \"custom_logs\" ]\nendpoint = \"http://loki.monitoring-system.svc.cluster.local:3100\" \n[sinks.vector_sink.encoding]\ncodec = \"json\"\n[sinks.vector_sink.labels]\nname = \"veritable_custom_logs_" + veritable.tenant + "\""}  # noqa
    )

    body = k8s_dynamic_client.client.sanitize_for_serialization(body)

    k8s_dynamic_client.server_side_apply(
        resource=resource,
        body=body,
        field_manager="kubectl-client-side-apply"
    )


async def create_configmap(veritable: VeritableSpec) -> None:
    """
    Create configmap in k8s
    :param veritable:
    :return:
    """
    # generate fernet key and insert into 1Password if not exists
    environment: str = os.getenv("DEPLOYMENT", "integration").lower()
    OnePasswordUtil(
        tenant=veritable.tenant,
        server_item=f"veritable-tenant-config-{environment}",
        vault=OnepasswordVaultName
    ).insert_if_not_exists("fernet_key", Fernet.generate_key().decode())

    apply_tenant_config(veritable)
    apply_provisioning_config(veritable)
    apply_env_config(veritable)
    apply_vector_config(veritable)


async def delete_configmap(tenant_name: str) -> None:
    """
    Delete configmap in k8s
    :param tenant_name:
    :return:
    """
    k8s_dynamic_client = get_dynamic_client()
    resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.ConfigMap, api_version="v1")

    k8s_dynamic_client.delete(resource=resource, name=TenantConfigMap.name, namespace=tenant_name)
    k8s_dynamic_client.delete(resource=resource, name=ProvisioningConfigMap.name, namespace=tenant_name)
    k8s_dynamic_client.delete(resource=resource, name=EnvConfigMap.name, namespace=tenant_name)
    k8s_dynamic_client.delete(resource=resource, name=VectorConfigMap.name, namespace=tenant_name)