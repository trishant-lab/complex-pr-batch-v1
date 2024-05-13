import socket
import time

from google.api_core.exceptions import Conflict, NotFound
from google.cloud import dns
from loguru import logger


class GoogleDNS:

    client = dns.Client()

    def __init__(self, cname, fqdn, zone_name):
        self.cname = cname
        self.fqdn = fqdn
        self.zone_name = zone_name
        self.zone = self.client.zone(name=zone_name)

    def create_dns(self):
        """
        Create DNS record in Google Cloud DNS
        :return:
        """
        try:
            changes = self.zone.changes()
            record_set = dns.ResourceRecordSet(
                name=self.fqdn,
                record_type="CNAME",
                ttl=86400,  # 1 day in seconds
                rrdatas=[self.cname],
                zone=self.zone
            )
            changes.add_record_set(record_set)
            changes.create()

            logger.info(f"DNS record created: {self.fqdn}")
        except Conflict:
            logger.info(f"DNS record Already Present: {self.fqdn}")

    def check_dns_propagation_cf(self):
        """
        Check DNS propagation using Cloudflare DNS
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
                    raise Exception(f"DNS propagation check timed out after [10 min]: {self.fqdn}")
                logger.info(f"DNS not propagated yet: {self.fqdn}")
                time.sleep(5)

    def delete(self):
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
                zone=zone
            )
            changes.delete_record_set(record_set)
            changes.create()
        except NotFound:
            logger.info(f"DNS record not found: {self.fqdn}")
