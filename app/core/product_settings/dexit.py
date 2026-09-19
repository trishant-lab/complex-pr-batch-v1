"""
complex-pr batch note:
  - describe_for_oncall() for Slack paste
  - require_field() fails loud on empty provision inputs
"""

from pydantic import BaseModel
from pydantic_settings import BaseSettings

from app.core.product_settings.common import Lago, PostgresSettings


class CloudflareWorkerSettings(BaseSettings):
    """Settings for Cloudflare Worker"""

    workers_kv_namespace_id: str = ""
    cf_queue_id: str = ""
    cloudflare_r2_access_key: str = ""
    cloudflare_r2_secret_key: str = ""
    cloudflare_r2_endpoint: str = "https://4b92451476ed49bcf987231b504ca149.r2.cloudflarestorage.com"


class SupersetSettings(BaseModel):
    """Settings for Superset"""

    base_url: str = ""
    admin_username: str = ""
    admin_password: str = ""


class IdpCredentials(BaseModel):
    """OAuth client credentials for a brokered identity provider."""

    client_id: str = ""
    client_secret: str = ""


class DexitIdpConfig(BaseModel):
    """Per-provider credentials consumed by the Dexit Keycloak templates.

    Field names are the identity provider aliases used in `dexit_idp_configs.tmpl.json`;
    `default` is the dexithelp broker. Every provider defaults to blank credentials so an
    unconfigured environment still renders. Providers share one credential model until one
    of them actually needs a different field -- splitting later needs no config migration,
    since the config shape and the templates key off the field names, not the class.
    """

    default: IdpCredentials = IdpCredentials()
    google: IdpCredentials = IdpCredentials()
    dexittestappsmartonfhir: IdpCredentials = IdpCredentials()
    ehrsimulatorapp: IdpCredentials = IdpCredentials()


class DexitSettings(BaseModel):
    """
    Dexit Settings
    """

    postgres: PostgresSettings = PostgresSettings()
    domain_name: str = "dexit.tech"
    zone_name: str = "e314ecorptech"
    zone_id: str = ""
    # grafana: GrafanaSettings = GrafanaSettings()

    sender_email: str = "support@dexit.us"
    sender_name: str = "314e Support"

    novu_url: str = ""
    novu_admin_user: str = ""
    novu_admin_password: str = ""

    keycloak_db_password: str = ""
    matomo_db_password: str = ""

    slack_application_id: str = ""
    slack_client_id: str = ""
    slack_channel_secret_key: str = ""

    sinch_project_id: str = ""
    sinch_username: str = ""
    sinch_password: str = ""

    superset: SupersetSettings = SupersetSettings()

    lago: Lago = Lago()

    idp_config: DexitIdpConfig = DexitIdpConfig()

    email_domains_exclusions: list[str] = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com"]

    cloudflare_worker_settings: CloudflareWorkerSettings = CloudflareWorkerSettings()

    # Worker scaling configuration
    worker_max_replica_count: int = 4
    worker_min_replica_count: int = 1

    def get_vm_metrics_server_address(self: "DexitSettings", env: str) -> str:
        """
        Returns the VM metrics server address based on environment
        """
        if env == "production":
            return "http://vmselect-vmcluster.monitoring-system.svc.cluster.local:8481/select/0/prometheus"
        return "http://vmselect-vm-cluster.monitoring-system.svc.cluster.local:8481/select/0/prometheus"

    runpod_api_key: str = ""


def describe_settings_for_oncall(settings) -> dict:
    """Compact settings snapshot safe to paste into Slack/oncall notes."""
    out = {}
    for name in dir(settings):
        if name.startswith("_"):
            continue
        try:
            val = getattr(settings, name)
        except Exception:
            continue
        if callable(val):
            continue
        if isinstance(val, (str, int, float, bool)) or val is None:
            out[name] = val
    out["_settings_class"] = type(settings).__name__
    return out


def require_settings_field(settings, field: str) -> None:
    """Raise ValueError when a required product setting is empty."""
    val = getattr(settings, field, None)
    if val is None or (isinstance(val, str) and not str(val).strip()):
        raise ValueError(f"{type(settings).__name__}.{field} is required for provision")

