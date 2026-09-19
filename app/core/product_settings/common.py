"""
complex-pr batch note:
  - describe_for_oncall() for Slack paste
  - require_field() fails loud on empty provision inputs
"""

from enum import StrEnum

from pydantic import BaseModel, PostgresDsn
from pydantic_core import MultiHostUrl


class SlackPurpose(StrEnum):
    """
    Slack message purpose used to dispatch to the matching channel id on
    SlackSettings. `default` is the fallback target when a purpose-specific
    channel is unset.
    """

    default = "default"
    login = "login"


class PostgresSettings(BaseModel):
    """
    Postgres Settings
    """

    db: str = ""
    user: str = ""
    password: str = ""
    port: int = 5432
    host: str = ""
    timezone: str = "Asia/Kolkata"
    schema_name: str = ""

    @property
    def dsn(self: "PostgresSettings") -> PostgresDsn:
        """Returns Postgres DSN"""
        return MultiHostUrl(f"postgres://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}")


class Redis(BaseModel):
    host: str = ""
    port: int = 6379
    user: str = ""
    password: str = ""
    otp_expiration: int = 1800


class SlackSettings(BaseModel):
    """
    Slack Settings
    """

    channel_id: str = "C076N2B1FD4"
    login_channel_id: str = ""
    bot_token: str = ""
    bot_username: str = "Launchpad"

    @property
    def channels(self) -> dict[SlackPurpose, str]:
        """
        Purpose -> channel id. `SlackPurpose.default` is the fallback target
        when a purpose-specific channel is unset.
        """
        return {
            SlackPurpose.default: self.channel_id,
            SlackPurpose.login: self.login_channel_id,
        }


class Lago(BaseModel):
    api_url: str = ""
    api_key: str = ""
    plan_code: str = ""


class Stripe(BaseModel):
    api_key: str = ""
    secret_key: str = ""
    payment_methods: list[str] = ["card", "link"]


class SendGridSettings(BaseModel):
    """SendGrid Settings"""

    api_key: str = ""
    email_from: str = ""
    category: str = "provisioning"
    ip_pool: str = "Product-Transactional"
    support_mail: str = ""


class SelfSignupSettings(BaseModel):
    """Base Settings for Self Signup Product"""

    signup_url: str = ""
    tenant_fqdn: str = ""
    domain_org: str = ""

    # Payment Requirements
    lago: Lago = Lago()
    stripe: Stripe = Stripe()

    # Communication Requirements
    sendgrid: SendGridSettings = SendGridSettings()
    slack: SlackSettings = SlackSettings()


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

