from functools import lru_cache

from loguru import logger
from slack_sdk import WebClient

from app.core.product_settings.common import SlackSettings
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


def get_slack_settings(product: ProductEnum) -> SlackSettings:
    """
    Return the SlackSettings instance for the given product.
    """
    match product:
        case ProductEnum.veritable:
            return config.veritable.slack
        case ProductEnum.pricedx:
            return config.pricedx.slack
        case _:
            return config.slack


def send_slack_msg(
    product: ProductEnum,
    text: str,
    blocks: list[dict],
    channel_id: str | None = None,
) -> None:
    """
    Post a slack message for the given product. When channel_id is provided,
    it overrides the product's default channel; otherwise the product's
    default channel_id is used.
    """
    try:
        slack_cfg = get_slack_settings(product)
        target_channel = channel_id or slack_cfg.channel_id
        client = get_slack_client(product)
        client.chat_postMessage(
            channel=target_channel,
            text=text,
            blocks=blocks,
            username=slack_cfg.bot_username,
        )
    except Exception as e:
        logger.error(f"Error sending message to slack: {e!r}")
