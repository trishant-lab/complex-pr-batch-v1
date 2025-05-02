import os
from functools import lru_cache, partial
from typing import Final

import httpx
from loguru import logger
from pydantic import BaseModel, ConfigDict, SecretStr
from pydantic_settings import BaseSettings

from app.core.ijson import ijson_loads
from app.core.product_settings.common import PostgresSettings, Redis, SlackSettings
from app.core.product_settings.dexit import DexitSettings
from app.core.product_settings.hdp import HDPSettings
from app.core.product_settings.jeeves import JeevesSettings
from app.core.product_settings.muspell_archive import MuspellArchiveSettings
from app.core.product_settings.penknife import PenknifeSettings
from app.core.product_settings.practifly import PractiflySettings
from app.core.product_settings.pricedx import PricedxSettings
from app.core.product_settings.veritable import VeritableSettings
from app.core.product_settings.zsegment import ZSegmentSettings
from app.utils.file_operations import get_opendal_file_client

CONFIG_FILE_NAMES: Final[list[str]] = [
    "settings.json",
    "jeeves.json",
    "dexit.json",
    "muspell_archive.json",
    "penknife.json",
    "zsegment.json",
    "practifly.json",
    "veritable.json",
    "pricedx.json",
]
PRODUCT_FILE_NAMES: Final[list[str]] = [
    "veritable.json",
    "jeeves.json",
    "dexit.json",
    "muspell_archive.json",
    "penknife.json",
    "zsegment.json",
    "practifly.json",
    "pricedx.json",
]


class KeycloakSettings(BaseModel):
    """
    Keycloak Settings
    """

    realm: str = "launchpad"

    admin_realm: str = "master"
    admin_client_id: str = "admin-temporal"
    username: str = "k8s-operator"
    password: str = ""

    client_id: str = "app"
    auth_url: str = "https://auth.314ecorp.tech"
    internal_auth_url: str = "http://keycloak-service.keycloak.svc.cluster.local:8080"  # NOSONAR
    auth_user: str = "installer"
    auth_secret: str = ""
    keycloak_db_password: str = ""

    realm_path: str = "/auth/admin/realms/"

    @property
    def wellknown_url(self: "KeycloakSettings") -> str:
        """Returns keycloak well-known url"""
        return f"{self.auth_url}/auth/realms/{self.realm}/.well-known/openid-configuration"


class GrafanaSettings(BaseModel):
    """
    Grafana Settings
    """

    dashboard_uid: str = ""
    datasource_uid: str = ""
    folder_uid: str = ""
    alert_folder_uid: str = ""


class TemporalSettings(BaseModel):
    """Temporal Settings"""

    host: str = "localhost"
    port: str = "7233"
    namespace: str = "launchpad"

    @property
    def dsn(self: "TemporalSettings") -> str:
        """Returns Temporal DSN"""
        return f"{self.host}:{self.port}"


class DockerRegistrySettings(BaseModel):
    """Docker Registry Settings"""

    registry_url: str = "https://registry.314ecorp.tech"
    registry_username: str = ""
    registry_password: str = ""


class S3Settings(BaseModel):
    """
    S3 Settings
    """

    endpoint: str = ""
    access_key: str = ""
    secret_key: str = ""
    region: str = "us-east-1"
    use_ssl: bool = True
    s3_alias: str = "launchpad"
    bucket: str = ""


class SendGridSettings(BaseModel):
    """SendGrid Settings"""

    api_key: str = ""
    email_from: str = ""
    support_mail: str = ""
    category: str = "provisioning"


class GSuiteModel(BaseSettings):
    type: str = "service_account"
    project_id: str = "e235711"

    private_key_id: SecretStr = SecretStr("")
    private_key: SecretStr = SecretStr("")

    client_email: str = ""

    client_id: str = ""
    customer_id: str = ""
    gsuite_admin: str = "kesav@314ecorp.com"

    auth_uri: str = "https://accounts.google.com/o/oauth2/auth"
    token_uri: str = "https://oauth2.googleapis.com/token"
    auth_provider_x509_cert_url: str = "https://www.googleapis.com/oauth2/v1/certs"
    client_x509_cert_url: str = (
        "https://www.googleapis.com/robot/v1/metadata/x509/app-314e%40e235711.iam.gserviceaccount.com"
    )

    model_config = ConfigDict(extra="ignore")


class CloudflareSettings(BaseModel):
    """
    Cloudflare Settings
    """

    account_id: str = ""
    api_token: str = ""
    access_key: str = ""
    s3_alias: str = "launchpad"
    r2_endpoint: str = "https://4b92451476ed49bcf987231b504ca149.r2.cloudflarestorage.com"
    r2_secret_key: str = ""
    r2_access_key: str = ""
    api_url: str = "https://api.cloudflare.com/client/v4/"
    bucket_read_permission_group_id: str = ""
    bucket_read_permission_group_name: str = "Workers R2 Storage Bucket Item Read"
    bucket_write_permission_group_id: str = ""
    bucket_write_permission_group_name: str = "Workers R2 Storage Bucket Item Write"


class DigitalOceanSettings(BaseModel):
    """
    DigitalOcean Settings
    """

    api_token: str = ""
    region: str = "sfo3"
    size: str = "s-1vcpu-1gb"
    image: str = "ubuntu-24-04-x64"
    ssh_key_name: str = "314e"


class Recaptcha(BaseSettings):
    api_url: str = ""
    secret_key: str = ""


class AppSettings(BaseSettings):
    """
    Application Settings
    """

    env: str = os.getenv("DEPLOYMENT", "integration").lower()
    api_prefix: str = "/api/v1"
    client_code: str = "launchpad"
    billing_url: str = ""

    keycloak: KeycloakSettings = KeycloakSettings()
    keycloak_prod: KeycloakSettings = KeycloakSettings()
    postgres: PostgresSettings = PostgresSettings()
    pg_super_admin: PostgresSettings = PostgresSettings()
    slack: SlackSettings = SlackSettings()
    sendgrid: SendGridSettings = SendGridSettings()
    cloudflare: CloudflareSettings = CloudflareSettings()
    docker_registry: DockerRegistrySettings = DockerRegistrySettings()

    veritable: VeritableSettings = VeritableSettings()
    jeeves: JeevesSettings = JeevesSettings()
    dexit: DexitSettings = DexitSettings()
    penknife: PenknifeSettings = PenknifeSettings()
    hdp: HDPSettings = HDPSettings()
    zsegment: ZSegmentSettings = ZSegmentSettings()
    practifly: PractiflySettings = PractiflySettings()
    pricedx: PricedxSettings = PricedxSettings()
    muspell: MuspellArchiveSettings = MuspellArchiveSettings()
    temporal: TemporalSettings = TemporalSettings()
    s3_int: S3Settings = S3Settings()
    s3: S3Settings = S3Settings()
    r2: S3Settings = S3Settings()
    redis: Redis = Redis()
    recaptcha: Recaptcha = Recaptcha()

    matomo_db_password: str = ""

    docker_image_pull_secret: str = ""
    google_dns_cname: str = "k8s.314ecorp.tech."
    k8s_cname: str = "k8s.314ecorp.tech."

    digitalocean: DigitalOceanSettings = DigitalOceanSettings()

    grafana_url: str = "https://monitor.314ecorp.tech"
    grafana_datasource_uid: str = ""
    grafana_token: str = ""

    supavisor_url: str = "http://supavisor-cluster-ha.supavisor.svc.cluster.local:4000"  # NOSONAR
    supavisor_token: str = ""

    cache_admin_password: str = ""

    app_url: str = "https://launchpad.314ecorp.tech/sprint"

    log_path: str = "/var/log" if os.getuid() == 0 else get_opendal_file_client().tempdir_root
    log_file_path: str = os.path.join(log_path, "launchpad_app.log")

    gsuite: GSuiteModel = GSuiteModel()

    kube_config_path: str = ".kube/config"

    model_config = ConfigDict(extra="ignore")

    @property
    def is_env_integration(self: "AppSettings") -> bool:
        """
        Returns true if env is integration
        @return:
        """
        return self.env == "integration"


class IntegrationSettings(AppSettings):
    """
    Integration Settings
    """

    keycloak: KeycloakSettings = KeycloakSettings()
    postgres: PostgresSettings = PostgresSettings()
    gsuite: GSuiteModel = GSuiteModel()

    billing_url: str = "https://api-billing.314ecorp.tech"
    app_url: str = "https://launchpad.314ecorp.tech/sprint"

    model_config = ConfigDict(extra="ignore")


class ProductionSettings(AppSettings):
    """
    Production Settings
    """

    keycloak: KeycloakSettings = KeycloakSettings()
    postgres: PostgresSettings = PostgresSettings()

    billing_url: str = "https://api-billing.314ecorp.com"
    app_url: str = "https://launchpad.314ecorp.com"
    grafana_datasource_uid: str = "LTvkszRVk"

    model_config = ConfigDict(extra="ignore")


@lru_cache
def get_settings() -> AppSettings:
    """
    This function initializes the settings object based on environment DEPLOYMENT. The order in which
    the settings are applied is as follows:

    DEPLOYMENT environment creates right settings object.  This is the default base object.
    If APP_CONFIG_FILE is specified it loads all the data defined from the file
    """
    deployment: str = os.getenv("DEPLOYMENT", "integration").lower()
    config_dir = os.getenv("APP_CONFIG_DIR", "/")
    default_settings = ProductionSettings() if deployment == "production" else IntegrationSettings()

    combined_config = dict()
    fs_client = get_opendal_file_client()
    for file in CONFIG_FILE_NAMES:
        if file in PRODUCT_FILE_NAMES:
            product = file.split(".")[0]
            try:
                file_content = fs_client.read_file_sync_str(os.path.join(config_dir, file))
                combined_config.update({product: ijson_loads(file_content)})
            except Exception as e:
                logger.error(f"Error while loading config for {product}: {e}")
        else:
            try:
                file_content = fs_client.read_file_sync_str(os.path.join(config_dir, file))
                combined_config.update(ijson_loads(file_content))
            except Exception:
                logger.error(f"found inadequate config file - {file}, returning default settings!")

    import pydash as py_

    default_settings_dict = default_settings.model_dump()
    default_settings_dict_partial = partial(py_.set_, default_settings_dict)

    for key, val in combined_config.items():
        default_settings_dict_partial(key, val)

    return default_settings.model_validate(default_settings_dict)


@lru_cache
def get_security_config() -> dict:
    """
    Returns keycloak endpoints
    """
    settings: AppSettings = get_settings()
    return httpx.get(settings.keycloak.wellknown_url, timeout=60).json()


APP_CONFIG: AppSettings = get_settings()
