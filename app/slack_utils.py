from enum import Enum
from functools import lru_cache

from loguru import logger
from slack_sdk import WebClient

from app.core.product_settings.common import SlackSettings
from app.core.settings import AppSettings, get_settings
from app.models.product import ProductEnum

config: AppSettings = get_settings()


class SlackChannel(str, Enum):
    signup = "signup"
    login = "login"


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


def _resolve_channel(slack_cfg: SlackSettings, channel: SlackChannel) -> str:
    """
    Pick the channel id for the given kind. Login falls back to signup
    channel when login_channel_id is unset.
    """
    if channel is SlackChannel.login:
        return slack_cfg.login_channel_id or slack_cfg.channel_id
    return slack_cfg.channel_id


def _send_message(product: ProductEnum, text: str, blocks: list[dict], channel: SlackChannel) -> None:
    """
    Send message to channel
    """
    try:
        client = get_slack_client(product)
        match product:
            case ProductEnum.veritable:
                slack_cfg = config.veritable.slack
            case ProductEnum.pricedx:
                slack_cfg = config.pricedx.slack
            case _:
                slack_cfg = config.slack

        channel_id = _resolve_channel(slack_cfg, channel)
        username = slack_cfg.bot_username

        client.chat_postMessage(
            channel=channel_id,
            text=text,
            blocks=blocks,
            username=username,
        )
    except Exception as e:
        logger.error(f"Error sending message to slack: {e!r}")


def send_slack_msg(
    product: ProductEnum,
    text: str,
    blocks: list[dict],
    channel: SlackChannel = SlackChannel.signup,
) -> None:
    """
    @param text: plain text message
    @param blocks: blocks for msg formatting
    @param channel: signup (default) or login
    """
    _send_message(product=product, text=text, blocks=blocks, channel=channel)
