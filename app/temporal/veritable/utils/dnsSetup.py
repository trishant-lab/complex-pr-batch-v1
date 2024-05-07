from app.core.settings import AppSettings, get_settings
from app.temporal.common.googleDNS import GoogleDNS
from app.temporal.veritable.utils.common import VeritableSpec, ProductName


async def dns_setup(veritable: VeritableSpec):
    config: AppSettings = get_settings()

    domain_name: str = config.product_config.get(ProductName).domain_name

    google_dns = GoogleDNS(
        cname=f"{config.google_dns_cname}.",
        fqdn=f"{veritable.tenant}.{domain_name}.",
        zone_name="veritableapp"
    )

    # create dns
    google_dns.create_dns()

    # check dns propagation
    google_dns.check_dns_propagation_cf()
