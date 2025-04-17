from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.activity_utils.check_kube_config_certificate import check_kube_config_certificate_expiry
from app.cli.temporal.core.base import Activity


class KubeConfigCertExpiryActivity(Activity):
    @staticmethod
    def get_timeout() -> timedelta:
        """
        @return:
        """
        return timedelta(seconds=10)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        @return:
        """
        return RetryPolicy(maximum_attempts=4, maximum_interval=timedelta(seconds=10))

    @staticmethod
    @activity.defn(name="KubeConfigCertExpiryActivity")
    async def defn(activity_input: None) -> None:
        """
        activity to check kube config certificate expiry and send mail if it is expired within one week
        """
        await check_kube_config_certificate_expiry()
