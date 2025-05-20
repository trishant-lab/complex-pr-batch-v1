from pydantic import BaseModel

from app.core.product_settings.common import Lago, PostgresSettings


class ZSegmentSettings(BaseModel):
    """
    ZSegment Settings with environment-based configuration.
    """

    postgres: PostgresSettings = PostgresSettings()
    domain_name: str = ""
    zone_name: str = ""
    zone_id: str = ""
    redpanda_broker: str = ""
    redpanda_admin_username: str = ""
    redpanda_admin_password: str = ""
    redpanda_admin_api_base_url: str = ""
    keycloak_auth_server_url: str = ""
    gitea_base_url: str = ""
    gitea_admin_username: str = ""
    gitea_admin_password: str = ""
    gitea_template_owner: str = ""
    lago: Lago = Lago()
    postgres_url: str = ""
    matomo_auth_token: str = ""
    sender_name: str = ""
    sender_email: str = ""
    victoria_metrics_url: str = ""
    grafana_api_url: str = ""
    grafana_api_key: str = ""
    digital_ocean_token: str = ""
    omniflow_server_url: str = ""

    deb_url: str = ""
    email_domains_exclusions: list[str] = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com"]
