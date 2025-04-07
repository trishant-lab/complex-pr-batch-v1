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

    pg_dsn_template: str = "postgresql://jeeves_{tenant}.jeeves_{tenant}:{password}@supavisor-cluster-ha.supavisor.svc.cluster.local:6543/jeeves"
    atlas_pg_dsn_template: str = (
        "postgresql://jeeves_{tenant}:{password}@db-cluster-ha.postgresql.svc.cluster.local/jeeves"
    )
    redis_dsn_template: str = "redis://redis:@cache.{tenant}.svc.cluster.local"
    base_ui_url: str = "https://{tenant}.okjeeves.tech"
    s3_mpd_api: str = "https://{tenant}.api.okjeeves.app/public/api/v1/recording/getMPDFile"
    mpd_api: str = "https://{tenant}.api.okjeeves.app/api/v1/asset"
    auth_secret: str = ""
    email_domains_exclusions: list[str] = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com"]
