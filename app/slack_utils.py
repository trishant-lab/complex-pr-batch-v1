from functools import lru_cache

from slack_sdk import WebClient

from app.core.settings import get_settings, AppSettings

config: AppSettings = get_settings()


@lru_cache
def get_slack_client() -> WebClient:
    """
    Return a slack client
    """
    return WebClient(token=config.slack.bot_token)


def _send_message(channel_id: str, text: str, blocks: list[dict]) -> None:
    """
    Send message to channel
    """
    # Send a message
    client = get_slack_client()
    client.chat_postMessage(
        channel=channel_id,
        text=text,
        blocks=blocks,
        username=config.slack.bot_username,
    )


def send_slack_msg(text: str, blocks: list[dict]) -> None:
    """
    @param text: plain text message
    @param blocks: blocks for msg formatting
    """
    _send_message(channel_id=config.slack.channel_id, text=text, blocks=blocks)
