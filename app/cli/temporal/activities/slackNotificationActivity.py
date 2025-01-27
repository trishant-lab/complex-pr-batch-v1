from datetime import timedelta
import traceback
from typing import Any
from loguru import logger
from temporalio import activity
from temporalio.common import RetryPolicy
from slack_sdk.errors import SlackApiError

from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.slack_utils import send_slack_msg


class SlackNotificationActivityModel(LaunchpadCLIBaseModel):
    error_message: str
    product: str
    exception: Any | None = None


class SlackNotifier:
    def __init__(self, product: str, error_message: str, exception: Any | None = None) -> None:
        self.product = product
        self.error_message = error_message
        self.exception = exception

    def send_notification(self) -> bool:
        """
        Send a notification to Slack
        """
        try:
            if self.exception:
                tb = traceback.extract_tb(self.exception.__traceback__)
                last_frame = tb[-1]
                error_context = f"Code: {last_frame.line}"
                exception_msg: str = f"Traceback:\n{error_context}\n"
                error_message = f"{self.error_message} :{self.product} - {exception_msg}"
            else:
                error_message = f"{self.error_message} :{self.product}"
            send_slack_msg(text=error_message, blocks=[])
        except SlackApiError as slack_error:
            logger.error(f"Failed to send Slack notification: {slack_error}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Slack notification: {e}")
            return False


class SlackNotificationActivity(Activity):
    """
    SlackNotificationActivity
    """

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=120)

    @staticmethod
    @activity.defn(name="SlackNotificationActivity")
    async def defn(activity_model: SlackNotificationActivityModel) -> None:
        """
        Callable for the activity
        """
        slack_notification = SlackNotifier(product=activity_model.product, error_message=activity_model.error_message)
        slack_notification.send_notification()
