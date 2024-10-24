import asyncio
from datetime import timedelta
import socket
from google.cloud import dns

from temporalio import activity
from temporalio.common import RetryPolicy
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_info


class DnsSetupActivityModel(LaunchpadCLIBaseModel):
    """
    DnsSetupActivityModel
    """

    cname: str
    fqdn: str
    zone_name: str


class DnsSetupActivity(Activity):
    """
    DnsSetupActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)

    @staticmethod
    @activity.defn(name="DnsSetupActivity")
    async def defn(activity_model: DnsSetupActivityModel) -> None:
        """
        Callable for the activity
        """
        client = dns.Client()

        zone = client.zone(activity_model.zone_name)
        changes = zone.changes()

        record_set = dns.ResourceRecordSet(
            name=activity_model.fqdn,
            record_type="CNAME",
            ttl=1 * 60 * 60,  # 1 hour in seconds
            rrdatas=[activity_model.cname],
            zone=zone,
        )

        changes.add_record_set(record_set)
        changes.create()

        log_info(f"DNS record created: {activity_model.fqdn}")

        # check DNS propagation
        count = 0
        while True:
            try:
                socket.getaddrinfo(activity_model.fqdn, 0)
                break
            except socket.gaierror:
                count += 1
                if count == 61:
                    raise Exception(f"DNS propagation check timed out after [10 min]: {activity_model.fqdn}")
                log_info(f"DNS not propagated yet: {activity_model.fqdn}")
                await asyncio.sleep(10)
