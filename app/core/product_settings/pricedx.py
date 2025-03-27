from pydantic import BaseModel

from app.core.product_settings.common import PostgresSettings


class PricedxSettings(BaseModel):
    """
    Pricedx Settings
    """

    postgres: PostgresSettings = PostgresSettings()
    domain_name: str = "pricedx.tech"

    zone_id: str = ""

    sender_email: str = "developer@314ecorp.com"
    sender_name: str = "Pricedx Support"

    location_hint: str = "enam"

    pg_dsn_template: str = "postgresql://pricedx_{tenant}.pricedx_{tenant}:{password}@supavisor-cluster-ha.supavisor.svc.cluster.local:6543/pricedx"
    redis_dsn_template: str = "redis://redis:@cache.{tenant}.svc.cluster.local"
    base_ui_url: str = "https://{tenant}.pricedx.tech"

    lago_api_url: str = ""
    lago_plan_code: str = ""
    lago_api_key: str = ""
