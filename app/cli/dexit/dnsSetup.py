from app.core.settings import AppSettings, get_settings
from app.cli.common.GoogleDNS import Googledns
from app.cli.dexit.dexit import DexitSpec


async def dns_setup(dexit: DexitSpec) -> None:
    """
    Setup DNS
    """
    config: AppSettings = get_settings()

    domain_name: str = config.dexit.domain_name

    google_dns = Googledns(
        cname=f"{config.google_dns_cname}.", fqdn=f"{dexit.tenant}.{domain_name}.", zone_name="e314ecorptech"
    )

    # create dns
    google_dns.create_dns()

    # check dns propagation
    await google_dns.check_dns_propagation()


async def dns_teardown(tenant_name: str) -> None:
    """
    Teardown DNS
    """
    config: AppSettings = get_settings()

    domain_name: str = config.dexit.domain_name

    google_dns = Googledns(
        cname=f"{config.google_dns_cname}.", fqdn=f"{tenant_name}.{domain_name}.", zone_name="e314ecorptech"
    )

    # delete dns
    google_dns.delete()
