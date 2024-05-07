import time

import orjson
import requests
from google.cloud import dns

from loguru import logger


class GoogleDNS:

    def __init__(self, cname, fqdn, zone_name):
        self.cname = cname
        self.fqdn = fqdn
        self.zone_name = zone_name

    def create_dns(self):
        """
        Create DNS record in Google Cloud DNS
        :return:
        """
        client = dns.Client()
        zone = client.zone(name=self.zone_name)

        # Check if DNS already exists
        record_sets = zone.list_resource_record_sets()
        for record in record_sets:
            if record.name == self.fqdn:
                logger.info(f"DNS record Already Present: {self.fqdn}")
                return

        # Create new DNS record
        changes = zone.changes()
        record_set = dns.ResourceRecordSet(
            name=self.fqdn,
            record_type="CNAME",
            ttl=86400,  # 1 day in seconds
            rrdatas=[self.cname],
            zone=zone
        )
        changes.add_record_set(record_set)
        changes.create()

        logger.info(f"DNS record created: {self.fqdn}")

    def check_dns_propagation_cf(self):
        """
        Check DNS propagation using Cloudflare DNS
        :return:
        """
        count = 0
        while True:
            response = requests.get(
                f"https://cloudflare-dns.com/dns-query?name={self.fqdn}&&type=CNAME",
                headers={"accept": "application/dns-json"}
            )
            node = orjson.loads(response.text)
            status = node.get("Status")

            if status == 0:
                logger.info(f"DNS Propagated: {self.fqdn}")
                break
            else:
                logger.info(f"Check Failed, Retrying Propagation Check [10s]: {self.fqdn}")
                # Request Retry Time [10 Seconds]
                count += 1
                time.sleep(10)

            if count == 61:
                raise Exception(f"DNS propagation check timed out after [10 min]: {self.fqdn}")

    def delete(self):
        """
        Delete DNS record in Google Cloud DNS
        """
        client = dns.Client()
        zone = client.zone(name=self.zone_name)

        # Check if DNS already exists
        record_sets = zone.list_resource_record_sets()
        for record in record_sets:
            if record.name == self.fqdn:
                break
        else:
            logger.info(f"DNS record Not Present: {self.fqdn}")
            return

        # Delete DNS record
        changes = zone.changes()
        record_set = dns.ResourceRecordSet(
            name=self.fqdn,
            record_type="CNAME",
            ttl=86400,  # 1 day in seconds
            rrdatas=[self.cname],
            zone=zone
        )
        changes.delete_record_set(record_set)
