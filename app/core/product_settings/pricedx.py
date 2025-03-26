from pydantic import BaseModel

from app.core.product_settings.common import PostgresSettings


class PricedxSettings(BaseModel):
    """
    Pricedx Settings
    """

    postgres: PostgresSettings = PostgresSettings()
    domain_name: str = "pricedx.tech"

    zone_id: str = ""

    sender_email: str = "support@priced.com"
    sender_name: str = "Pricedx Support"

    keycloak_smtp_password: str = ""

    prod_image_tag: str = ""

    keycloak_db_password: str = ""
    matomo_db_password: str = ""

    location_hint: str = "enam"

    r2_url: str = ""
    r2_access_key: str = ""
    r2_secret: str = ""
    r2_bucket: str = ""

    reporting_site_id: str = "1"

    pg_dsn_template: str = "postgresql://pricedx_{tenant}.pricedx_{tenant}:{password}@supavisor-cluster-ha.supavisor.svc.cluster.local:6543/pricedx"
    atlas_pg_dsn_template: str = (
        "postgresql://pricedx_{tenant}:{password}@db-cluster-ha.postgresql.svc.cluster.local/pricedx"
    )
    redis_dsn_template: str = "redis://redis:@cache.{tenant}.svc.cluster.local"
    base_ui_url: str = "https://{tenant}.pricedx.tech"

