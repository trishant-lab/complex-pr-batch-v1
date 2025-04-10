from pydantic import BaseModel


class PostgresSettings(BaseModel):
    """
    Postgres Settings
    """

    db: str = ""
    user: str = ""
    password: str = ""
    port: int = 5432
    host: str = ""

    @property
    def dsn(self: "PostgresSettings") -> str:
        """Returns Postgres DSN"""
        return f"postgres://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    timezone: str = "Asia/Kolkata"
    schema_name: str = ""


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
    billing_url: str = ""
    tenant_fqdn: str = ""
    domain_org: str = ""

    # Payment Requirements
    lago: Lago = Lago()
    stripe: Stripe = Stripe()

    # Communication Requirements
    sendgrid: SendGridSettings = SendGridSettings()
    slack: SlackSettings = SlackSettings()
