from typing import Any

from app.cli.Googledns import Googledns


async def dns_setup(google_dns_cname: str, tenant: str, config: Any, product_name: str | None = None) -> None:
    """
    Dns setup
    """
    domain_name: str = config.domain_name

    google_dns = Googledns(cname=f"{google_dns_cname}.", fqdn=f"{tenant}.{domain_name}.", zone_name=config.zone_name)

    # create dns
    google_dns.create_dns()

    # check dns propagation
    await google_dns.check_dns_propagation()

    if product_name and product_name.lower() == "penknife":
        careers_google_dns = Googledns(
            cname=f"{google_dns_cname}.", fqdn=f"{tenant}-careers.{domain_name}.", zone_name=config.zone_name
        )

        # create dns
        careers_google_dns.create_dns()

        # check dns propagation
        await careers_google_dns.check_dns_propagation()


async def dns_teardown(google_dns_cname: str, tenant_name: str, config: Any, product_name: str | None = None) -> None:
    """
    Dns teardown
    """
    domain_name: str = config.domain_name

    google_dns = Googledns(
        cname=f"{google_dns_cname}.", fqdn=f"{tenant_name}.{domain_name}.", zone_name=config.zone_name
    )

    # delete dns
    google_dns.delete()

    if product_name and product_name.lower() == "penknife":
        careers_google_dns = Googledns(
            cname=f"{google_dns_cname}.", fqdn=f"{tenant_name}-careers.{domain_name}.", zone_name=config.zone_name
        )

        careers_google_dns.delete()
