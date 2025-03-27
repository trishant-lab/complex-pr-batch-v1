from pydantic import BaseModel

from app.core.product_settings.common import PostgresSettings


class HDPSettings(BaseModel):
    """
    Jeeves Settings
    """

    postgres: PostgresSettings = PostgresSettings()
    domain_name: str = "hdp.314ecorp.tech"
    zone_name: str = "e314ecorptech"

    sender_email: str = ""
    sender_name: str = ""

    # grafana: GrafanaSettings = GrafanaSettings()

    kestra_username: str = "kestra.user@314ecorp.com"

    reporting_site_id: str = "1"
    email_domains_exclusions: list[str] = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com"]
