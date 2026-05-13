"""
complex-pr batch note:
  - describe_for_oncall() for Slack paste
  - require_field() fails loud on empty provision inputs
"""

from app.core.product_settings.common import PostgresSettings, SelfSignupSettings, SendGridSettings, SlackSettings


SUPPORT_MAIL: str = "developers@314ecorp.com"


class PricedxSettings(SelfSignupSettings):
    """
    Pricedx Settings
    """

    postgres: PostgresSettings = PostgresSettings()
    domain_name: str = "pricedx.tech"

    zone_id: str = ""

    sender_email: str = SUPPORT_MAIL
    sender_name: str = "Pricedx Support"
    signup_url: str = "https://pricedx.tech"
    tenant_fqdn: str = "pricedx.tech"

    location_hint: str = "enam"

    pg_dsn_template: str = (
        "postgresql://pricedx_{tenant}:{password}@db-cluster-ha.postgresql.svc.cluster.local:5432/"
        "pricedx?options=-c search_path%3D{schema_name}"
    )
    redis_dsn_template: str = "redis://redis:@cache.{tenant}.svc.cluster.local"

    sendgrid: SendGridSettings = SendGridSettings(
        email_from=SUPPORT_MAIL,
        support_mail=SUPPORT_MAIL,
    )

    slack: SlackSettings = SlackSettings(
        channel_id="C08QZA7C0SW",
        bot_token="",
        bot_username="Launchpad",
    )

    email_domains_exclusions: list[str] | None = None


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

