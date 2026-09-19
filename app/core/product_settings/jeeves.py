"""
complex-pr batch note:
  - describe_for_oncall() for Slack paste
  - require_field() fails loud on empty provision inputs
"""

from pydantic import BaseModel

from app.core.product_settings.common import PostgresSettings


class JeevesSettings(BaseModel):
    """
    Jeeves Settings
    """

    postgres: PostgresSettings = PostgresSettings()
    domain_name: str = "okjeeves.tech"
    # zone_name: str = "e314ecorptech"
    zone_id: str = ""
    kv_namespace_id: str = ""
    queue_message_retention_period: int = 14 * 24 * 60 * 60  # seconds; 14 days, Cloudflare's maximum
    queue_consumer_max_retries: int = 10  # delivery attempts before a message is dropped; Cloudflare allows at most 100
    outbound_queue_name_template: str = "jeeves-{tenant}-{space}-outbound"
    workers_kv_key_template: str = "{tenant}-{space}"
    # grafana: GrafanaSettings = GrafanaSettings()

    sender_email: str = "support@okjeeves.com"
    sender_name: str = "Jeeves Support"

    novu_url: str = ""
    novu_admin_user: str = "jeeves.assistant@314ecorp.com"
    novu_admin_password: str = ""
    novu_sendgrid_sender_email: str = "noreply@okjeeves.com"
    novu_sendgrid_sender_name: str = "Jeeves Support"

    chatwoot_base_url: str = "http://chatwoot.chatwoot.svc.cluster.local:3000"  # NOSONAR
    chatwoot_platform_api_token: str = ""
    chatwoot_default_user_password: str = ""
    chatwoot_domain: str = "314ecorp.tech"
    server_url: str = ""

    keycloak_smtp_password: str = ""

    vespa_host: str = ""
    vespa_deploy_port_address: str = ""
    vespa_user_index_suffix: str = "_user"
    vespa_application_path: str = "/vespa/jeeves/application"

    prod_image_tag: str = ""
    idp_config: dict = {}

    keycloak_db_password: str = ""
    matomo_db_password: str = ""

    location_hint: str = "enam"

    tika_server_endpoint: str = "http://tika-server.tika.svc.cluster.local:9998"  # NOSONAR

    r2_url: str = ""
    r2_access_key: str = ""
    r2_secret: str = ""
    r2_bucket: str = ""

    reporting_site_id: str = "1"

    pg_dsn_template: str = "postgresql://jeeves_{tenant}.jeeves_{tenant}:{password}@{supavisor_host}/jeeves"
    supavisor_host: str = "supavisor-cluster-ha.supavisor.svc.cluster.local:6543"
    atlas_pg_dsn_template: str = "postgresql://jeeves_{tenant}:{password}@{atlas_pg_host}/jeeves"
    atlas_pg_host: str = "db-cluster-ha.postgres16.svc.cluster.local"
    redis_dsn_template: str = "redis://redis:@cache.{tenant}.svc.cluster.local"
    base_ui_url: str = "https://{tenant}.okjeeves.tech"
    s3_mpd_api: str = "https://{tenant}.api.okjeeves.app/public/api/v1/recording/getMPDFile"
    mpd_api: str = "https://{tenant}.api.okjeeves.app/api/v1/asset"
    auth_secret: str = ""
    keycloak_attribute_to_match_user: str = "username"
    ehr_field_to_match_user: str = "SYSLOGIN"
    email_domains_exclusions: list[str] = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com"]
    posthog_username: str = "posthog_ro"


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

