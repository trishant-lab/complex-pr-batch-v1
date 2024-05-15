import os
from functools import partial
from typing import Final

import loguru
import orjson
from pydantic import BaseModel, ConfigDict
from pydantic_settings import BaseSettings

CONFIG_FILE_NAMES: Final[list[str]] = ["settings.json", "veritable.json", "jeeves.json"]
PRODUCT_FILE_NAMES: Final[list[str]] = ["veritable.json", "jeeves.json"]


class KeycloakSettings(BaseModel):
    """
    Keycloak Settings
    """

    realm: str = "onboarding"

    admin_realm: str = "master"
    admin_client_id: str = "admin-temporal"
    username: str = "k8s-operator"
    password: str = ""

    client_id: str = "app"
    client_secret: str = ""
    auth_url: str = "https://auth.314ecorp.tech"


class PostgresSettings(BaseModel):
    """
    Postgres Settings
    """

    db: str = ""
    user: str = ""
    password: str = ""
    port: int = 5432
    host: str = ""

    @property
    def dsn(self: "PostgresSettings") -> str:
        """Returns Postgres DSN"""
        return f"postgres://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    timezone: str = "Asia/Kolkata"
    schema_name: str = ""


class GrafanaSettings(BaseModel):
    """
    Grafana Settings
    """
    dashboard_uid: str = ""
    datasource_uid: str = ""
    folder_uid: str = ""
    alert_folder_uid: str = ""


class ProductConfig(BaseModel):
    """
    Product Config
    """
    postgres: PostgresSettings = PostgresSettings()
    domain_name: str = ""  # Domain name for the product e.g. int.veritable.app or jeeves.314ecorp.tech
    grafana: GrafanaSettings = GrafanaSettings()


class TemporalSettings(BaseModel):
    """Temporal Settings"""

    host: str = "localhost"
    port: str = "7233"
    namespace: str = "onboarding"

    @property
    def dsn(self: "TemporalSettings") -> str:
        """Returns Temporal DSN"""
        return f"{self.host}:{self.port}"


class S3Settings(BaseModel):
    """
    S3 Settings
    """
    endpoint: str = ""
    access_key: str = ""
    secret_key: str = ""
    bucket_name: str = ""
    region: str = "us-east-1"
    use_ssl: bool = True
    rclone_remote: str = "s3_rclone_remote"


class VeritableSettings(BaseModel):
    """
    Veritable Settings

    """
    postgres: PostgresSettings = PostgresSettings()
    domain_name: str = "int.veritable.app"
    grafana: GrafanaSettings = GrafanaSettings()

    temporal_veritable_onboarding_task_queue: str = "temporal_veritable_onboarding_task_queue"
    temporal_veritable_deboarding_task_queue: str = "temporal_veritable_deboarding_task_queue"
    temporal_veritable_postgres_setup_task_queue: str = "temporal_veritable_postgres_setup_task_queue"


class AppSettings(BaseSettings):
    """
    Application Settings
    """

    env: str = os.getenv("DEPLOYMENT", "integration").lower()

    keycloak: KeycloakSettings = KeycloakSettings()
    postgres: PostgresSettings = PostgresSettings()
    veritable: VeritableSettings = VeritableSettings()

    temporal: TemporalSettings = TemporalSettings()
    s3: S3Settings = S3Settings()

    docker_image_pull_secret: str = ""
    google_dns_cname: str = "k8s.31ecorp.tech"

    sendgrid_api_key: str = ""

    grafana_url: str = ""
    grafana_token: str = ""

    supavisor_url: str = "http://supavisor-cluster-ha.supavisor.svc.cluster.local:4000"
    supavisor_token: str = ""

    model_config = ConfigDict(extra="ignore")


class IntegrationSettings(AppSettings):
    """
    Integration Settings
    """
    keycloak: KeycloakSettings = KeycloakSettings()
    postgres: PostgresSettings = PostgresSettings()
    model_config = ConfigDict(extra="ignore")


class ProductionSettings(AppSettings):
    """
    Production Settings
    """
    keycloak: KeycloakSettings = KeycloakSettings()
    postgres: PostgresSettings = PostgresSettings()
    model_config = ConfigDict(extra="ignore")


def get_settings():
    """
    This function initializes the settings object based on environment DEPLOYMENT. The order in which
    the settings are applied is as follows:

    DEPLOYMENT environment creates right settings object.  This is the default base object.
    If APP_CONFIG_FILE is specified it loads all the data defined from the file
    """
    deployment: str = os.getenv("DEPLOYMENT", "integration").lower()
    config_dir = os.getenv("APP_CONFIG_DIR", "/")
    config_files = [x.path for x in os.scandir(config_dir) if x.name in CONFIG_FILE_NAMES]
    default_settings = ProductionSettings() if deployment == "production" else IntegrationSettings()
    if len(config_files) != len(CONFIG_FILE_NAMES):
        loguru.logger.info(
            f"found inadequate config files - {orjson.dumps(config_files)}, returning default settings!",
        )
        return default_settings

    combined_config = dict()
    for file in CONFIG_FILE_NAMES:
        if file in PRODUCT_FILE_NAMES:
            product = file.split(".")[0]
            try:
                combined_config[product] = orjson.loads(open(os.path.join(config_dir, file)).read())
            except Exception as e:
                loguru.logger.error(f"Error while loading config for {product}: {e}")
        else:
            combined_config.update(orjson.loads(open(os.path.join(config_dir, file)).read()))

    import pydash as py_

    default_settings_dict = default_settings.dict()
    default_settings_dict_partial = partial(py_.set_, default_settings_dict)

    for key, val in combined_config.items():
        default_settings_dict_partial(key, val)

    settings = default_settings.model_validate(default_settings_dict)
    return settings
