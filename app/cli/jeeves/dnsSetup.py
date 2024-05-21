from app.core.settings import AppSettings, get_settings
from app.cli.common.googleDNS import GoogleDNS
from app.cli.jeeves.common import JeevesSpec, ProductName


async def dns_setup(jeeves: JeevesSpec):
    config: AppSettings = get_settings()

    domain_name: str = config.jeeves.domain_name

    google_dns = GoogleDNS(
        cname=f"{config.google_dns_cname}.",
        fqdn=f"{jeeves.tenant}.{domain_name}.",
        zone_name="e314ecorptech"
    )

    # create dns
    google_dns.create_dns()

    # check dns propagation
    await google_dns.check_dns_propagation_cf()


async def dns_teardown(tenant_name: str):
    config: AppSettings = get_settings()

    domain_name: str = config.jeeves.domain_name

    google_dns = GoogleDNS(
        cname=f"{config.google_dns_cname}.",
        fqdn=f"{tenant_name}.{domain_name}.",
        zone_name="e314ecorptech"
    )

    # delete dns
    google_dns.delete()
