from typing import Any

from app.cli.common.Googledns import Googledns


async def dns_setup(tenant: str, config: Any) -> None:
    """
    Dns setup
    """
    domain_name: str = config.domain_name

    google_dns = Googledns(
        cname=f"{config.google_dns_cname}.", fqdn=f"{tenant}.{domain_name}.", zone_name=config.zone_name
    )

    # create dns
    google_dns.create_dns()

    # check dns propagation
    await google_dns.check_dns_propagation()


async def dns_teardown(tenant_name: str, config: Any) -> None:
    """
    Dns teardown
    """
    domain_name: str = config.domain_name

    google_dns = Googledns(
        cname=f"{config.google_dns_cname}.", fqdn=f"{tenant_name}.{domain_name}.", zone_name=config.zone_name
    )

    # delete dns
    google_dns.delete()
