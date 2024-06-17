from app.core.settings import AppSettings, get_settings
from app.cli.common.Googledns import Googledns
from app.cli.veritable.models.veritableSpec import VeritableSpec


async def dns_setup(veritable: VeritableSpec) -> None:
    """
    Setup DNS for veritable
    """
    config: AppSettings = get_settings()

    domain_name: str = config.veritable.domain_name

    google_dns = Googledns(
        cname=f"{config.google_dns_cname}.", fqdn=f"{veritable.tenant}.{domain_name}.", zone_name="veritableapp"
    )

    # create dns
    google_dns.create_dns()

    # check dns propagation
    await google_dns.check_dns_propagation()


async def dns_teardown(tenant_name: str) -> None:
    """
    Teardown DNS for veritable
    """
    config: AppSettings = get_settings()

    domain_name: str = config.veritable.domain_name

    google_dns = Googledns(
        cname=f"{config.google_dns_cname}.", fqdn=f"{tenant_name}.{domain_name}.", zone_name="veritableapp"
    )

    # delete dns
    google_dns.delete()
