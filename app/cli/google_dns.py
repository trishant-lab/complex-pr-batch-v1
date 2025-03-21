import asyncio
import socket

from app.cli.temporal.core.log import log_info
from google.api_core.exceptions import Conflict, NotFound
from google.cloud import dns


class Googledns:
    client = dns.Client()

    def __init__(self: "Googledns", cname: str, fqdn: str, zone_name: str) -> None:
        """
        Initialize googleDNS
        """
        self.cname = cname
        self.fqdn = fqdn
        self.zone_name = zone_name
        self.zone = self.client.zone(name=zone_name)

    def create_dns(self: "Googledns") -> None:
        """
        Create DNS record in Google Cloud DNS
        :return:
        """
        try:
            changes = self.zone.changes()
            record_set = dns.ResourceRecordSet(
                name=self.fqdn,
                record_type="CNAME",
                ttl=1,  # 1 day in seconds
                rrdatas=[self.cname],
                zone=self.zone,
            )
            changes.add_record_set(record_set)
            changes.create()

            log_info(message=f"DNS record created: {self.fqdn}")
        except Conflict:
            log_info(message=f"DNS record Already Present: {self.fqdn}")

    async def check_dns_propagation(self: "Googledns") -> None:
        """
        Check DNS propagation using Socket
        :return:
        """
        count = 0
        while True:
            try:
                socket.getaddrinfo(self.fqdn, 0)
                break
            except socket.gaierror:
                count += 1
                if count == 61:
                    raise TimeoutError(f"DNS propagation check timed out after [10 min]: {self.fqdn}")
                log_info(f"DNS not propagated yet: {self.fqdn}")
                await asyncio.sleep(10)

    def delete(self: "Googledns") -> None:
        """
        Delete DNS record in Google Cloud DNS
        """
        client = dns.Client()
        zone = client.zone(name=self.zone_name)

        # Delete DNS record
        try:
            changes = zone.changes()
            record_set = dns.ResourceRecordSet(
                name=self.fqdn,
                record_type="CNAME",
                ttl=86400,  # 1 day in seconds
                rrdatas=[self.cname],
                zone=zone,
            )
            changes.delete_record_set(record_set)
            changes.create()
        except NotFound:
            log_info(f"DNS record not found: {self.fqdn}")
