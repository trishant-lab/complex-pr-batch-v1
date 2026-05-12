from functools import lru_cache
from typing import Literal

from loguru import logger
from slack_sdk import WebClient

from app.core.product_settings.common import SlackSettings
from app.core.settings import AppSettings, get_settings
from app.models.product import ProductEnum

config: AppSettings = get_settings()

SlackPurpose = Literal["signup", "login"]

_CHANNEL_FIELD_BY_PURPOSE: dict[SlackPurpose, str] = {
    "signup": "channel_id",
    "login": "login_channel_id",
}


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


def _resolve_channel(slack_cfg: SlackSettings, product: ProductEnum, purpose: SlackPurpose) -> str:
    """
    Map purpose to the configured channel id, falling back to the product's
    signup channel when the requested purpose has no channel configured.
    Warns on fallback so misconfig is visible.
    """
    channel_id: str = getattr(slack_cfg, _CHANNEL_FIELD_BY_PURPOSE[purpose])
    if channel_id:
        return channel_id
    if purpose != "signup":
        logger.warning(
            "slack purpose={} unset for product={}; falling back to signup channel",
            purpose,
            product.value,
        )
    return slack_cfg.channel_id


def send_slack_msg(
    product: ProductEnum,
    text: str,
    blocks: list[dict],
    purpose: SlackPurpose = "signup",
) -> None:
    """
    Post a slack message for the given product to the channel configured for
    the requested purpose.
    """
    try:
        slack_cfg = get_slack_settings(product)
        channel_id = _resolve_channel(slack_cfg, product, purpose)
        client = get_slack_client(product)
        client.chat_postMessage(
            channel=channel_id,
            text=text,
            blocks=blocks,
            username=slack_cfg.bot_username,
        )
    except Exception as e:
        logger.error(f"Error sending message to slack: {e!r}")
