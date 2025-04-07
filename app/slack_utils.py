from functools import lru_cache

from slack_sdk import WebClient

from app.core.settings import AppSettings, get_settings
from app.models.product import ProductEnum

config: AppSettings = get_settings()


@lru_cache(maxsize=10)
def get_slack_client(product: ProductEnum) -> WebClient:
    """
    Return a slack client
    """
    match product:
        case ProductEnum.veritable:
            return WebClient(token=config.veritable.slack.bot_token)
        case _:
            return WebClient(token=config.slack.bot_token)


def _send_message(product: ProductEnum, text: str, blocks: list[dict]) -> None:
    """
    Send message to channel
    """
    # Send a message
    client = get_slack_client(product)
    match product:
        case ProductEnum.veritable:
            channel_id = config.veritable.slack.channel_id
            username = config.veritable.slack.bot_username
        case _:
            channel_id = config.slack.channel_id
            username = config.slack.bot_username

    client.chat_postMessage(
        channel=channel_id,
        text=text,
        blocks=blocks,
        username=username,
    )


def send_slack_msg(product: ProductEnum, text: str, blocks: list[dict]) -> None:
    """
    @param text: plain text message
    @param blocks: blocks for msg formatting
    """
    _send_message(product=product, text=text, blocks=blocks)
