from pydantic import BaseModel, PostgresDsn
from pydantic_core import MultiHostUrl


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
    bot_token: str = ""
    bot_username: str = "Launchpad"


class Lago(BaseModel):
    api_url: str = ""
    api_key: str = ""
    plan_code: str = ""


class Stripe(BaseModel):
    api_key: str = ""
    secret_key: str = ""


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
