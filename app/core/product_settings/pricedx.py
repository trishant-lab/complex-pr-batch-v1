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
