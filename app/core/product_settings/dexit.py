from pydantic import BaseModel

from app.core.product_settings.common import Lago, PostgresSettings


class DexitSettings(BaseModel):
    """
    Dexit Settings
    """

    postgres: PostgresSettings = PostgresSettings()
    domain_name: str = "dexit.tech"
    zone_name: str = "e314ecorptech"
    zone_id: str = ""
    # grafana: GrafanaSettings = GrafanaSettings()

    sender_email: str = "developer@314ecorp.com"
    sender_name: str = "314e Support"

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

    lago: Lago = Lago()

    account_server_url: str = ""

    idp_config: dict = {}

    tika_server_endpoint: str = "http://tika-server.tika.svc.cluster.local:9998"  # NOSONAR
    email_domains_exclusions: list[str] = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com"]
