from app.core.product_settings.common import SelfSignupSettings, SendGridSettings

SUPPORT_MAIL: str = "support@veritable.app"
VERITABLE_ENGG_MAIL: str = "veritable-engg@veritable.app"


class VeritableSettings(SelfSignupSettings):
    """
    Veritable Settings
    """

    zone_id: str = ""
    domain_name: str = "veritable.work"
    sender_name: str = "Veritable"
    sender_email: str = ""

    domain_org: str = "app"
    signup_url: str = "https://test.veritable-app.pages.dev"
    onboarding_doc_url: str = "https://launchpad.veritable.app/Veritable/Veritable-Onboarding-Help.pdf"
    tenant_fqdn: str = "veritable.work"
    sendgrid: SendGridSettings = SendGridSettings(
        email_from=VERITABLE_ENGG_MAIL,
        support_mail=VERITABLE_ENGG_MAIL,
    )

    novu_url: str = "https://alerting.314ecorp.tech/"
    novu_admin_user: str = "support@veritable.app"
    novu_admin_password: str = ""
    email_domains_exclusions: list[str] | None = None
