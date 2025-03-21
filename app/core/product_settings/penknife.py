from pydantic import BaseModel

from app.core.product_settings.common import PostgresSettings


class PenknifeSettings(BaseModel):
    """
    Penknife Settings
    """

    postgres: PostgresSettings = PostgresSettings()
    domain_name: str = "penknife.tech"
    zone_id: str = ""
    zone_name: str = "e314ecorptech"

    sender_email: str = "developer@314ecorp.com"
    sender_name: str = "314e Support"

    novu_url: str = "https://alerting.314ecorp.tech"
    novu_admin_user: str = ""
    novu_admin_password: str = ""

    keycloak_db_password: str = ""
