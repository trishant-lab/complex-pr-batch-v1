import os
import tempfile
from enum import Enum
from functools import partial, lru_cache
from typing import Final

import loguru
import orjson
import requests
from pydantic import BaseModel, ConfigDict, SecretStr
from pydantic_settings import BaseSettings

from app.core.log import setup_logging

CONFIG_FILE_NAMES: Final[list[str]] = ["settings.json", "veritable.json", "jeeves.json", "dexit.json", "penknife.json"]
PRODUCT_FILE_NAMES: Final[list[str]] = ["veritable.json", "jeeves.json", "dexit.json", "penknife.json"]


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
    internal_auth_url: str = "http://keycloak-service.keycloak.svc.cluster.local:8080"
    auth_user: str = "installer"
    auth_secret: str = ""

    realm_path: str = "/auth/admin/realms/"

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
    region: str = "us-east-1"
    use_ssl: bool = True
    rclone_remote: str = "s3_rclone_remote"
    bucket: str = ""


class SlackSettings(BaseModel):
    """
    Slack Settings
    """

    channel_id: str = "C076N2B1FD4"
    bot_token: str = ""
    bot_username: str = "Launchpad"


class SendGridSettings(BaseModel):
    """SendGrid Settings"""

    api_key: str = ""
    email_from: str = "developer@314ecorp.com"
    category: str = "provisioning"


class GSuiteModel(BaseSettings):
    type: str = "service_account"
    project_id: str = "e235711"

    private_key_id: SecretStr = ""
    private_key: SecretStr = ""

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
    zone_name: str = "e314ecorptech"
    # grafana: GrafanaSettings = GrafanaSettings()

    temporal_jeeves_onboarding_task_queue: str = "temporal_jeeves_onboarding_task_queue"
    temporal_jeeves_deboarding_task_queue: str = "temporal_jeeves_deboarding_task_queue"

    novu_url: str = "https://alerting.314ecorp.tech"
    novu_admin_user: str = "jeeves.assistant@314ecorp.com"
    novu_admin_password: str = ""
    novu_sendgrid_sender_email: str = "noreply@okjeeves.com"
    novu_sendgrid_sender_name: str = "Jeeves Support"

    chatwoot_base_url: str = "https://jeeves-agent.314ecorp.tech/"
    chatwoot_platform_api_token: str = ""
    chatwoot_default_user_password: str = ""

    keycloak_db_password: str = ""
    matomo_db_password: str = ""

    tika_server_endpoint: str = "http://tika-server.tika.svc.cluster.local:9998"

    r2_url: str = ""
    r2_access_key: str = ""
    r2_secret: str = ""
    r2_bucket: str = ""

    reporting_site_id: str = "1"


class PenknifeSettings(BaseModel):
    """
    Penknife Settings
    """

    postgres: PostgresSettings = PostgresSettings()
    domain_name: str = "penknife.314ecorp.tech"
    zone_name: str = "e314ecorptech"

    temporal_penknife_onboarding_task_queue: str = "temporal_penknife_onboarding_task_queue"
    temporal_penknife_deboarding_task_queue: str = "temporal_penknife_deboarding_task_queue"

    novu_url: str = "https://alerting.314ecorp.tech"
    novu_admin_user: str = ""
    novu_admin_password: str = ""

    keycloak_db_password: str = ""

    # r2_url: str = ""
    # r2_access_key: str = ""
    # r2_secret: str = ""
    # r2_bucket: str = ""

    # reporting_site_id: str = "1"


class DexitAIOcrEngines(str, Enum):
    """OCR Engine"""

    TESSERACT = "tesseract"
    EASYOCR = "easyocr"
    DOCTR = "doctr"


class DexitAIEntityExtractionModels(str, Enum):
    """Entity Extraction Models"""

    LLAMA2_7B = "llama2:7b"
    LLAMA2_13B = "llama2:13b"
    LLAMA3_8B = "llama3:8b"
    LLAMA3_1_8B = "llama3.1:8b"
    GEMMA_7B = "gemma:7b"
    GEMMA2_9B = "gemma2:9b"


class DexitAIComputeEngineSettings(BaseModel):
    """
    Dexit AI Compute Engine Settings
    """

    accelerator: str = "cpu"
    instance_size: str = "x8"
    instance_type: str = "intel-spr"
    min_replica: int = 0
    max_replica: int = 1
    scale_to_zero_timeout: int = 15  # minutes
    vendor: str = "aws"
    region: str = "us-east-1"


class DexitAIEndpointSettings(BaseModel):
    """
    Dexit AI Endpoint Settings
    """

    enable_ocr: bool = True
    enable_entity_llm: bool = False
    enable_entity_layoutlm: bool = False
    enable_classification: bool = False
    compute_engine: DexitAIComputeEngineSettings = DexitAIComputeEngineSettings()


class DexitAISettings(BaseModel):
    """
    Dexit AI Settings
    """

    hf_username: str = "314e"
    hf_token_read: str = ""
    hf_token_write: str = ""
    hf_endpoint_repo_name: str = "314e/Dexit-AI"
    hf_endpoint_repo_revision: str = "production"

    ocr_engine: DexitAIOcrEngines = DexitAIOcrEngines.DOCTR

    classification_modelid: str = "314e/Dexit-LayoutLMv3-Classification-test1"
    classification_modelrevision: str = "v0.1.3-manual-upload"

    entity_layoutlm_modelid: str = "314e/Dexit-LayoutLMv3-Entity-test1"
    entity_layoutlm_modelrevision: str = "v0.1.6-test"

    entity_llm_modelname: DexitAIEntityExtractionModels = DexitAIEntityExtractionModels.LLAMA3_8B
    entity_llm_model_temperature: float = 0
    entity_llm_model_numctx: int = 4096
    entity_llm_model_numpredict: int = 300

    inference_endpoints: list[DexitAIEndpointSettings] = [DexitAIEndpointSettings()]


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
    client_code: str = "launchpad"

    keycloak: KeycloakSettings = KeycloakSettings()
    postgres: PostgresSettings = PostgresSettings()
    slack: SlackSettings = SlackSettings()
    sendgrid: SendGridSettings = SendGridSettings()

    veritable: VeritableSettings = VeritableSettings()
    jeeves: JeevesSettings = JeevesSettings()
    dexit: DexitSettings = DexitSettings()
    penknife: PenknifeSettings = PenknifeSettings()

    temporal: TemporalSettings = TemporalSettings()
    s3_int: S3Settings = S3Settings()
    s3: S3Settings = S3Settings()
    r2: S3Settings = S3Settings()

    docker_image_pull_secret: str = ""
    google_dns_cname: str = "k8s.314ecorp.tech"

    grafana_url: str = "https://monitor.314ecorp.tech"
    grafana_datasource_uid: str = "e4hhV8CGk"
    grafana_token: str = ""

    supavisor_url: str = "http://supavisor-cluster-ha.supavisor.svc.cluster.local:4000"
    supavisor_token: str = ""

    cache_admin_password: str = ""

    app_url: str = "https://launchpad.314ecorp.tech/sprint"

    log_path: str = "/var/log" if os.getuid() == 0 else tempfile.gettempdir()
    log_file_path: str = os.path.join(log_path, "launchpad_app.log")

    gsuite: GSuiteModel = GSuiteModel()

    model_config = ConfigDict(extra="ignore")


class IntegrationSettings(AppSettings):
    """
    Integration Settings
    """

    keycloak: KeycloakSettings = KeycloakSettings()
    postgres: PostgresSettings = PostgresSettings()
    gsuite: GSuiteModel = GSuiteModel()

    app_url: str = "https://launchpad.314ecorp.tech/sprint"

    model_config = ConfigDict(extra="ignore")


class ProductionSettings(AppSettings):
    """
    Production Settings
    """

    keycloak: KeycloakSettings = KeycloakSettings()
    postgres: PostgresSettings = PostgresSettings()

    app_url: str = "https://launchpad.314ecorp.com"
    grafana_datasource_uid: str = "LTvkszRVk"

    model_config = ConfigDict(extra="ignore")


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

    setup_logging(default_settings.log_path, default_settings.log_file_path)
    return default_settings.model_validate(default_settings_dict)


@lru_cache
def get_security_config() -> dict:
    """
    Returns keycloak endpoints
    """
    settings: AppSettings = get_settings()
    return requests.get(settings.keycloak.wellknown_url, timeout=60).json()
