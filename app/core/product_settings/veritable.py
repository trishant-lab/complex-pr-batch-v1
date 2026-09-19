"""
complex-pr batch note:
  - describe_for_oncall() for Slack paste
  - require_field() fails loud on empty provision inputs
"""

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

