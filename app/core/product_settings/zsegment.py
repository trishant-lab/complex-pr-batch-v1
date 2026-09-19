from pydantic import AliasChoices, BaseModel, Field

from app.core.product_settings.common import Lago, PostgresSettings


class ZSegmentSettings(BaseModel):
    """
    ZSegment Settings with environment-based configuration.
    """

    postgres: PostgresSettings = PostgresSettings()
    domain_name: str = ""
    zone_name: str = ""
    zone_id: str = ""
    keycloak_auth_server_url: str = ""
    gitea_base_url: str = ""
    gitea_admin_username: str = ""
    gitea_admin_password: str = ""
    gitea_template_owner: str = ""
    lago: Lago = Lago()
    postgres_url: str = ""
    sender_name: str = ""
    sender_email: str = ""
    victoria_metrics_url: str = ""
    grafana_api_url: str = ""
    grafana_api_key: str = ""
    # Empty falls back to the uid for the environment.
    grafana_datasource_uid: str = ""

    def resolved_grafana_datasource_uid(self, env_default: str) -> str:
        """Prefer the explicit setting; empty string means use env_default.

        Integration and production wire different VictoriaMetrics datasource
        uids. Keeping the empty-means-default rule here stops activities from
        hardcoding environment names.
        """
        return self.grafana_datasource_uid or env_default
    # integration and production name this key differently in their config files
    omniflow_base_url: str = Field("", validation_alias=AliasChoices("omniflow_base_url", "omniflow_server_url"))
    # Empty falls back to the tag for the environment.
    code_server_image_tag: str = ""
    # Empty resolves the newest published release tag for production, and
    # "sprint" elsewhere. Set it to pin a tenant to an exact release.
    image_tag: str = ""

    deb_url: str = ""
    email_domains_exclusions: list[str] = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com"]
