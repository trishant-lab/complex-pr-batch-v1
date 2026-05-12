from app.core.product_settings.common import SlackPurpose
from app.core.settings import get_settings
from app.models.lago.customer import CustomerResponse
from app.models.product import ProductEnum
from app.slack_utils import send_slack_msg

settings = get_settings()


def _get_leads_block_from_customer_response(text: str, customer: CustomerResponse) -> list[dict]:
    """
    @param customer:
    @return:
    """
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text,
            },
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Email:* {customer.email}",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Name:* {customer.name or customer.legal_name or ''}",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Phone:* {customer.phone or ''}",
                },
            ],
        },
    ]


def leads_otp_verified(email: str, product: ProductEnum, purpose: SlackPurpose = SlackPurpose.default) -> None:
    """
    @param email:
    send email to customer
    """
    text = "Customer has verified OTP"
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text,
            },
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Email:* {email}",
                },
            ],
        },
    ]
    send_slack_msg(product, text, blocks, purpose=purpose)


def leads_otp_sent(email: str, product: ProductEnum, purpose: SlackPurpose = SlackPurpose.default) -> None:
    """
    @param email:
    send email to customer
    """
    text = "Customer requested OTP"
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text,
            },
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Email:* {email}",
                },
            ],
        },
    ]
    send_slack_msg(product, text, blocks, purpose=purpose)


def leads_form_fill(
    customer: CustomerResponse, product: ProductEnum, purpose: SlackPurpose = SlackPurpose.default
) -> None:
    """
    @param customer:
    send email to customer
    """
    text = "Customer has filled 'Account Details' form"
    blocks = _get_leads_block_from_customer_response(text, customer)
    send_slack_msg(product, text, blocks, purpose=purpose)


def leads_add_payment_details(
    customer: CustomerResponse, product: ProductEnum, purpose: SlackPurpose = SlackPurpose.default
) -> None:
    """
    @param customer:
    send email to customer
    """
    text = "Customer has added 'Payment Information'"
    blocks = _get_leads_block_from_customer_response(text, customer)
    send_slack_msg(product, text, blocks, purpose=purpose)


def portal_link_otp_request(email: str, product: ProductEnum, purpose: SlackPurpose = SlackPurpose.default) -> None:
    """
    Notify slack: customer requested an OTP for a portal link (login flow).
    """
    text = f"{product.value} Portal Link OTP Request"
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text,
            },
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Email:* {email}",
                },
            ],
        },
    ]
    send_slack_msg(product, text, blocks, purpose=purpose)


def portal_link_request(
    email: str,
    product: ProductEnum,
    urls: list[str] | None = None,
    purpose: SlackPurpose = SlackPurpose.default,
) -> None:
    """
    Notify slack: customer redeemed a portal link (login flow).
    """
    text = f"{product.value} Portal Link Request"
    if urls:
        _urls = ", ".join(urls)
        url_payload = {
            "type": "mrkdwn",
            "text": f"*URLs:* {_urls}",
        }
    else:
        url_payload = {
            "type": "mrkdwn",
            "text": "Tenant doesn't exist or is no longer active",
        }
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text,
            },
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Email:* {email}",
                },
                url_payload,
            ],
        },
    ]
    send_slack_msg(product, text, blocks, purpose=purpose)
