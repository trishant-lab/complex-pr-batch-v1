from app.core.settings import AppSettings, get_settings
from app.cli.common.googleDNS import GoogleDNS
from app.cli.veritable.common import VeritableSpec, ProductName


async def dns_setup(veritable: VeritableSpec):
    config: AppSettings = get_settings()

    domain_name: str = config.veritable.domain_name

    google_dns = GoogleDNS(
        cname=f"{config.google_dns_cname}.",
        fqdn=f"{veritable.tenant}.{domain_name}.",
        zone_name="veritableapp"
    )

    # create dns
    google_dns.create_dns()

    # check dns propagation
    google_dns.check_dns_propagation_cf()


async def dns_teardown(tenant_name: str):
    config: AppSettings = get_settings()

    domain_name: str = config.veritable.domain_name

    google_dns = GoogleDNS(
        cname=f"{config.google_dns_cname}.",
        fqdn=f"{tenant_name}.{domain_name}.",
        zone_name="veritableapp"
    )

    # delete dns
    google_dns.delete()
