import os
from functools import lru_cache

from pydantic import BaseModel, ConfigDict
from pydantic_settings import BaseSettings


class KeycloakSettings(BaseModel):
    """
    Keycloak Settings
    """

    realm: str = "onboarding"

    admin_realm: str = "master"
    admin_client_id: str = "admin-cli"
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
    vault_name: str = ""  # OnePassword vault name for the product
    one_password_server_item: str = ""  # OnePassword server item for the product
    grafana: GrafanaSettings = GrafanaSettings()


class AppSettings(BaseSettings):
    """
    Application Settings
    """
    keycloak: KeycloakSettings = KeycloakSettings()
    postgres: PostgresSettings = PostgresSettings()
    product_config: dict[str, ProductConfig] = {}

    temporal_dsn: str = "localhost:7233"
    temporal_namespace: str = "onboarding"
    temporal_postgres_database_setup_task_queue: str = "temporal_postgres_database_setup_task_queue"
    temporal_keycloak_realm_creation_task_queue: str = "temporal_keycloak_realm_creation_task_queue"
    temporal_veritable_onboarding_task_queue: str = "temporal_veritable_onboarding_task_queue"
    temporal_veritable_deprovisioning_task_queue: str = "temporal_veritable_deprovisioning_task_queue"

    docker_image_pull_secret: str = ""
    google_dns_cname: str = "k8s.314ecorp.tech"

    s3_endpoint: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_use_ssl: bool = False
    s3_bucket_name: str = ""

    sendgrid_api_key: str = ""

    grafana_url: str = ""
    grafana_token: str = ""

    model_config = ConfigDict(extra="ignore")


class IntegrationSettings(AppSettings):
    """
    Integration Settings
    """
    keycloak: KeycloakSettings = KeycloakSettings()
    postgres: PostgresSettings = PostgresSettings()
    product_config: dict[str, ProductConfig] = {}

    model_config = ConfigDict(extra="ignore")


class ProductionSettings(AppSettings):
    """
    Production Settings
    """
    keycloak: KeycloakSettings = KeycloakSettings()
    postgres: PostgresSettings = PostgresSettings()
    product_config: dict[str, ProductConfig] = {}

    model_config = ConfigDict(extra="ignore")


def get_settings():
    """
    This function initializes the settings object based on environment DEPLOYMENT. The order in which
    the settings are applied is as follows:
    DEPLOYMENT environment creates right settings object.  This is the default base object.
    If APP_CONFIG_FILE is specified it loads all the data defined from the file
    """
    deployment: str = os.getenv("DEPLOYMENT", "integration").lower()
    settings: AppSettings = ProductionSettings() if deployment == "production" else IntegrationSettings()

    # If APP_CONFIG_FILE is provided update all settings from the file
    settings_file: str = os.getenv("APP_CONFIG_FILE")
    if settings_file is not None and os.path.exists(settings_file) and os.path.isfile(settings_file):
        settings = settings.model_validate_json(open(settings_file, "rb").read())

    config_dir = os.getenv("PRODUCT_CONFIG_DIR", "/")
    config_files = [x.path for x in os.scandir(config_dir)]
    for config_file in config_files:
        product_name = config_file.split("/")[-1].replace(".json", "").lower()
        settings.product_config[product_name] = (
            ProductConfig.model_validate_json(open(config_file, "rb").read())
        )

    return settings
