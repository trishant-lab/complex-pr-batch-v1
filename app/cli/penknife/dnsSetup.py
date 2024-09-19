from app.cli.penknife.models.penknifespec import PenknifeSpec
from app.core.settings import AppSettings, get_settings
from app.cli.common.GoogleDNS import Googledns


async def dns_setup(penknife: PenknifeSpec) -> None:
    """
    Dns setup
    """
    config: AppSettings = get_settings()

    domain_name: str = config.penknife.domain_name

    google_dns = Googledns(
        cname=f"{config.google_dns_cname}.", fqdn=f"{penknife.tenant}.{domain_name}.", zone_name="e314ecorptech"
    )

    # create dns
    google_dns.create_dns()

    # check dns propagation
    await google_dns.check_dns_propagation()


async def dns_teardown(tenant_name: str) -> None:
    """
    Dns teardown
    """
    config: AppSettings = get_settings()

    domain_name: str = config.penknife.domain_name

    google_dns = Googledns(
        cname=f"{config.google_dns_cname}.", fqdn=f"{tenant_name}.{domain_name}.", zone_name="e314ecorptech"
    )

    # delete dns
    google_dns.delete()
