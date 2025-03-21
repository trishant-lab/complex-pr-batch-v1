from app.core.product_settings.common import SelfSignupSettings, SendGridSettings

SUPPORT_MAIL: str = "support@veritable.app"
VERITABLE_ENGG_MAIL: str = "veritable-engg@veritable.app"


class VeritableSettings(SelfSignupSettings):
    """
    Veritable Settings
    """

    zone_id: str = ""
    domain_name: str = "veritable.tech"
    sender_name: str = ""
    sender_email: str = ""

    domain_org: str = "app"
    signup_url: str = "https://test.veritable-app.pages.dev"
    tenant_fqdn: str = "veritable.app"
    sendgrid: SendGridSettings = SendGridSettings(
        email_from=VERITABLE_ENGG_MAIL,
        support_mail=VERITABLE_ENGG_MAIL,
    )

    novu_url: str = "https://alerting.314ecorp.tech/"
    novu_admin_user: str = "support@veritable.app"
    novu_admin_password: str = ""
