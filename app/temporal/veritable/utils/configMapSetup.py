from tempfile import TemporaryDirectory

from cryptography.fernet import Fernet

from app.onepasswordutil import OnePasswordUtil, secret_inject
from app.template_env import get_env
from app.temporal.common.configMap import ConfigMap
from app.temporal.veritable.utils.common import VeritableSpec, OnepasswordVaultName, ProductName, TenantConfigMap, \
    ProvisioningConfigMap, EnvConfigMap, VectorConfigMap


def apply_tenant_config(veritable: VeritableSpec):
    """
    :return:
    """
    template_env = get_env(product=ProductName)
    template = template_env.get_template("integration-tenant-config.tmpl.json")
    output = template.render(
        tenant=veritable.tenant,
    )

    with TemporaryDirectory() as temp_dir:
        with open(f"{temp_dir}/integration-tenant-config.tmpl.json", "w") as f:
            f.write(output)

        # inject secret into tenant-config.json from 1Password
        secret_inject(
            source_file_path=f"{temp_dir}/integration-tenant-config.tmpl.json",
            destination_path=f"{temp_dir}/tenant-config.json"
        )

        # apply configmap in k8s namespace
        ConfigMap(namespace=veritable.tenant).create_or_replace_config(
            name=TenantConfigMap.name,
            data={TenantConfigMap.key: open(f"{temp_dir}/tenant-config.json").read()}
        )


def apply_provisioning_config(veritable: VeritableSpec):
    """
    :return:
    """
    template_env = get_env(product=ProductName)
    template = template_env.get_template("integration-provisioning-config.tmpl.json")
    output = template.render(
        tenant=veritable.tenant,
        customerId=veritable.customerId,
        orgName=veritable.orgName,
    )

    with TemporaryDirectory() as temp_dir:
        with open(f"{temp_dir}/integration-provisioning-config.tmpl.json", "w") as f:
            f.write(output)

        # inject secret into tenant-config.json from 1Password
        secret_inject(
            source_file_path=f"{temp_dir}/integration-provisioning-config.tmpl.json",
            destination_path=f"{temp_dir}/provisioning-config.json"
        )

        # apply configmap in k8s namespace
        ConfigMap(namespace=veritable.tenant).create_or_replace_config(
            name=ProvisioningConfigMap.name,
            data={ProvisioningConfigMap.key: open(f"{temp_dir}/provisioning-config.json").read()}
        )


def apply_env_config(veritable: VeritableSpec):
    """
    :return:
    """

    template_env = get_env(product=ProductName)
    template = template_env.get_template("integration-env-config.tmpl.json")
    output = template.render(
        tenant=veritable.tenant,
    )

    with TemporaryDirectory() as temp_dir:
        with open(f"{temp_dir}/integration-env-config.tmpl.json", "w") as f:
            f.write(output)

        # inject secret into tenant-config.json from 1Password
        secret_inject(
            source_file_path=f"{temp_dir}/integration-env-config.tmpl.json",
            destination_path=f"{temp_dir}/env-config.json"
        )

        # apply configmap in k8s namespace
        ConfigMap(namespace=veritable.tenant).create_or_replace_config(
            name=EnvConfigMap.name,
            data={EnvConfigMap.key: open(f"{temp_dir}/env-config.json").read()}
        )


def apply_vector_config(veritable: VeritableSpec):
    """
    :return:

    """
    ConfigMap(namespace=veritable.tenant).create_or_replace_config(
        name=VectorConfigMap.name,
        data={
            VectorConfigMap.key: "[log_schema]\nhost_key = \"host\"\nmessage_key = \"message\"\nsource_type_key = \"source_type\"\ntimestamp_key = \"timestamp\"\n\n# sources for logs\n\n[sources.custom_logs]\ntype = \"file\"\ninclude = [\"/var/log/supervisord/veritable_*\"]\nfingerprint.strategy = \"device_and_inode\"\n\n[sinks.vector_sink]\ntype = \"loki\"\ninputs = [ \"custom_logs\" ]\nendpoint = \"http://loki.monitoring-system.svc.cluster.local:3100\" \n[sinks.vector_sink.encoding]\ncodec = \"json\"\n[sinks.vector_sink.labels]\nname = \"veritable_custom_logs_" + veritable.tenant + "\""}
        # noqa
    )


async def create_configmap(veritable: VeritableSpec) -> None:
    """
    Create configmap in k8s
    :param veritable:
    :return:
    """
    # generate fernet key and insert into 1Password if not exists
    OnePasswordUtil(
        tenant=veritable.tenant,
        server_item=f"veritable-tenant-config-{veritable.environment}",
        vault=OnepasswordVaultName
    ).insert_if_not_exists("fernet_key", Fernet.generate_key().decode())

    apply_tenant_config(veritable)
    apply_provisioning_config(veritable)
    apply_env_config(veritable)
    apply_vector_config(veritable)
