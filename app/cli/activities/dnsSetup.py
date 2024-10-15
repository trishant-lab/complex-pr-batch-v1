from app.cli.Googledns import Googledns


async def dns_setup(google_dns_cname: str, fqdn: str, zone_name: str) -> None:
    """
    Dns setup
    """
    google_dns = Googledns(cname=f"{google_dns_cname}.", fqdn=fqdn, zone_name=zone_name)

    # create dns
    google_dns.create_dns()

    # check dns propagation
    await google_dns.check_dns_propagation()


async def dns_teardown(google_dns_cname: str, fqdn: str, zone_name: str) -> None:
    """
    Dns teardown
    """
    google_dns = Googledns(cname=f"{google_dns_cname}.", fqdn=fqdn, zone_name=zone_name)

    # delete dns
    google_dns.delete()
