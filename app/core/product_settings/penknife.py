"""
complex-pr batch note:
  - describe_for_oncall() for Slack paste
  - require_field() fails loud on empty provision inputs
"""

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
    email_domains_exclusions: list[str] = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com"]


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

