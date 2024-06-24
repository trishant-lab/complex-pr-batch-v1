import os
import requests
from enum import Enum
from functools import partial, lru_cache
from typing import Final, List

import loguru
import orjson
from pydantic import BaseModel, ConfigDict
from pydantic_settings import BaseSettings

CONFIG_FILE_NAMES: Final[list[str]] = ["settings.json", "veritable.json", "jeeves.json", "dexit.json"]
PRODUCT_FILE_NAMES: Final[list[str]] = ["veritable.json", "jeeves.json", "dexit.json"]


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

    @property
    def wellknown_url(self: "KeycloakSettings") -> str:
        """Returns keycloak well-known url"""
        return f"{self.auth_url}/auth/realms/{self.realm}/.well-known/openid-configuration"


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


class TemporalSettings(BaseModel):
    """Temporal Settings"""

    host: str = "localhost"
    port: str = "7233"
    namespace: str = "launchpad"

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


class SlackSettings(BaseModel):
    """
    Slack Settings
    """
    channel_id: str = "C076N2B1FD4"
    bot_token: str = ""
    bot_username: str = "Launchpad"


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


class JeevesSettings(BaseModel):
    """
    Jeeves Settings
    """
    postgres: PostgresSettings = PostgresSettings()
    domain_name: str = "jeeves.314ecorp.tech"
    # grafana: GrafanaSettings = GrafanaSettings()

    temporal_jeeves_onboarding_task_queue: str = "temporal_jeeves_onboarding_task_queue"
    temporal_jeeves_deboarding_task_queue: str = "temporal_jeeves_deboarding_task_queue"

    novu_url: str = "https://alerting.314ecorp.tech"
    novu_admin_user: str = "jeeves.assistant@314ecorp.com"
    novu_admin_password: str = ""

    chatwoot_base_url: str = "https://jeeves-agent.314ecorp.tech/"
    chatwoot_platform_api_token: str = ""
    chatwoot_default_user_password: str = ""

    keycloak_db_password: str = ""
    matomo_db_password: str = ""

    tika_server_endpoint: str = "http://tika-server.tika.svc.cluster.local:9998"
    
    
class DexitAIOcrEngines(str, Enum):
    """OCR Engine"""
    TESSERACT = 'tesseract'
    EASYOCR = 'easyocr'
    DOCTR = 'doctr'
    

class DexitAIEntityExtractionModels(str, Enum):
    """Entity Extraction Models"""
    LLAMA2_7B = 'llama2:7b'
    LLAMA2_13B = 'llama2:13b'


class DexitAIComputeEngineSettings(BaseModel):
    """
    Dexit AI Compute Engine Settings
    """
    accelerator: str = ''
    instance_size: str = ''
    instance_type: str = ''
    min_replica: int = 0
    max_replica: int = 1
    scale_to_zero_timeout: int = 15 # minutes
    vendor: str = ''
    region: str = 'us-east-1'
    

class DexitAIEndpointSettings(BaseModel):
    """
    Dexit AI Endpoint Settings
    """
    enable_ocr: bool = True
    enable_entity: bool = False
    enable_classification: bool = False
    compute_engine: DexitAIComputeEngineSettings = DexitAIComputeEngineSettings()
    

class DexitAISettings(BaseModel):
    """
    Dexit AI Settings
    """
    hf_username: str = '314e'
    hf_token_read: str = ''
    hf_token_write: str = ''
    hf_endpoint_repo_name: str = '314e/Dexit-AI'
    hf_endpoint_repo_revision: str = 'production'
    
    ocr_engine: DexitAIOcrEngines = DexitAIOcrEngines.TESSERACT
    
    classification_modelid: str = '314e/Dexit-Document-Classification-Muspell-Model1'
    classification_modelrevision: str = 'production'
    
    entity_modelname: DexitAIEntityExtractionModels = DexitAIEntityExtractionModels.LLAMA2_13B
    entity_model_temperature: float = 0
    entity_model_numctx: int = 4096
    entity_model_numpredict: int = 300
    
    inference_endpoints: List[DexitAIEndpointSettings] = [DexitAIEndpointSettings()]
    


class DexitSettings(BaseModel):
    """
    Dexit Settings
    """
    postgres: PostgresSettings = PostgresSettings()
    domain_name: str = "dexit.314ecorp.tech"
    # grafana: GrafanaSettings = GrafanaSettings()

    temporal_dexit_onboarding_task_queue: str = "temporal_dexit_onboarding_task_queue"
    temporal_dexit_deboarding_task_queue: str = "temporal_dexit_deboarding_task_queue"

    novu_url: str = "https://alerting.314ecorp.tech"
    novu_admin_user: str = "dexit.assistant@314ecorp.com"
    novu_admin_password: str = ""

    keycloak_db_password: str = ""
    matomo_db_password: str = ""

    slack_application_id: str = ""
    slack_client_id: str = ""
    slack_channel_secret_key: str = ""

    FaxAccountId: str = ""
    FaxApiToken: str = ""

    tika_server_endpoint: str = "http://tika-server.tika.svc.cluster.local:9998"
    
    ai_config: DexitAISettings = DexitAISettings()


class AppSettings(BaseSettings):
    """
    Application Settings
    """

    env: str = os.getenv("DEPLOYMENT", "integration").lower()
    api_prefix: str = "/api/v1"

    keycloak: KeycloakSettings = KeycloakSettings()
    postgres: PostgresSettings = PostgresSettings()
    slack: SlackSettings = SlackSettings()

    veritable: VeritableSettings = VeritableSettings()
    jeeves: JeevesSettings = JeevesSettings()
    dexit: DexitSettings = DexitSettings()

    temporal: TemporalSettings = TemporalSettings()
    s3: S3Settings = S3Settings()

    docker_image_pull_secret: str = ""
    google_dns_cname: str = "k8s.314ecorp.tech"

    sendgrid_api_key: str = ""

    grafana_url: str = ""
    grafana_token: str = ""

    supavisor_url: str = "http://supavisor-cluster-ha.supavisor.svc.cluster.local:4000"
    supavisor_token: str = ""

    cache_admin_password: str = ""

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
    # config_files = [x.path for x in os.scandir(config_dir) if x.name in CONFIG_FILE_NAMES]
    default_settings = ProductionSettings() if deployment == "production" else IntegrationSettings()
    # if len(config_files) != len(CONFIG_FILE_NAMES):
    #     loguru.logger.info(
    #         f"found inadequate config files - {orjson.dumps(config_files)}, returning default settings!",
    #     )
    #     return default_settings

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


@lru_cache
def get_security_config():
    """
    Returns keycloak endpoints
    """
    settings: AppSettings = get_settings()
    return requests.get(settings.keycloak.wellknown_url).json()
