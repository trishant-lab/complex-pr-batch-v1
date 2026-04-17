from app.core.settings import get_settings
from app.models.lago.customer import CustomerResponse
from app.models.product import ProductEnum
from app.slack_utils import send_slack_msg

settings = get_settings()


def _send_lead_msg(text: str, blocks: list[dict], product: ProductEnum) -> None:
    """
    Send integration msg to slack & production to marketing channel
    """
    send_slack_msg(product, text, blocks)


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


def leads_otp_verified(email: str, product: ProductEnum) -> None:
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
    _send_lead_msg(text, blocks, product)


def leads_otp_sent(email: str, product: ProductEnum) -> None:
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
    _send_lead_msg(text, blocks, product)


def leads_form_fill(customer: CustomerResponse, product: ProductEnum) -> None:
    """
    @param customer:
    send email to customer
    """
    text = "Customer has filled 'Account Details' form"
    blocks = _get_leads_block_from_customer_response(text, customer)
    _send_lead_msg(text, blocks, product)


def leads_add_payment_details(customer: CustomerResponse, product: ProductEnum) -> None:
    """
    @param customer:
    send email to customer
    """
    text = "Customer has added 'Payment Information'"
    blocks = _get_leads_block_from_customer_response(text, customer)
    _send_lead_msg(text, blocks, product)
