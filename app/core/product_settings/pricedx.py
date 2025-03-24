from app.core.product_settings.common import SelfSignupSettings, SendGridSettings

SUPPORT_MAIL: str = "support@pricedx.app"
PRICEDX_ENGG_MAIL: str = "pricedx-engg@pricedx.app"

class PricedxSettings(SelfSignupSettings):
    """
    Pricedx Settings
    """

    zone_id: str = ""
    domain_name: str = "pricedx.tech"
    sender_name: str = ""
    sender_email: str = ""
    lago_api_url: str = ""
    lago_plan_code: str = ""
    lago_api_key: str = ""

    domain_org: str = "app"
    signup_url: str = "https://pricedx.tech"
    tenant_fqdn: str = "pricedx.tech"
    sendgrid: SendGridSettings = SendGridSettings(
        email_from=PRICEDX_ENGG_MAIL,
        support_mail=PRICEDX_ENGG_MAIL,
    )
