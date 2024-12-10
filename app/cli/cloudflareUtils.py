from cloudflare import AsyncCloudflare
from cloudflare.types.r2 import TemporaryCredentialCreateResponse
from loguru import logger
import requests

from app.core.settings import AppSettings


async def get_cloudflare_client(config: AppSettings) -> AsyncCloudflare:
    """
    Get a Cloudflare client
    """
    return AsyncCloudflare(api_token=config.cloudflare.api_token)


async def get_temporary_credentials(config: AppSettings, bucket_name: str) -> TemporaryCredentialCreateResponse:
    """
    Get temporary credentials
    """
    client: AsyncCloudflare = await get_cloudflare_client(config=config)
    return await client.r2.temporary_credentials.create(
        account_id=config.cloudflare.account_id,
        bucket=bucket_name,
        parent_access_key_id=config.cloudflare.access_key,
        permission="object-read-write",
        ttl_seconds=10 * 60,
    )


async def get_bucket(config: AppSettings, bucket_name: str) -> list:
    """
    Get a bucket
    """
    client: AsyncCloudflare = await get_cloudflare_client(config=config)
    response = await client.r2.buckets.list(account_id=config.cloudflare.account_id, name_contains=bucket_name)
    return response.result.get("buckets", [])


async def create_bucket(config: AppSettings, bucket_name: str) -> dict | None:
    """
    Create a bucket
    """
    client: AsyncCloudflare = await get_cloudflare_client(config=config)
    if not await get_bucket(config=config, bucket_name=bucket_name):
        return await client.r2.buckets.create(account_id=config.cloudflare.account_id, name=bucket_name)
    return None


async def delete_bucket(config: AppSettings, bucket_name: str) -> dict:
    """
    Delete a bucket
    """
    client: AsyncCloudflare = await get_cloudflare_client(config=config)
    return await client.r2.buckets.delete(account_id=config.cloudflare.account_id, bucket_name=bucket_name)


async def get_dns_record(config: AppSettings, fqdn: str, zone_id: str) -> list:
    """
    Get a DNS record
    """
    client: AsyncCloudflare = await get_cloudflare_client(config=config)
    response = await client.dns.records.list(zone_id=zone_id, name=fqdn, type="CNAME")
    return response.result


async def create_dns_record(config: AppSettings, fqdn: str, zone_id: str) -> dict:
    """
    Create a DNS record
    """
    client: AsyncCloudflare = await get_cloudflare_client(config=config)

    # check if the record already exists
    if await get_dns_record(config=config, fqdn=fqdn, zone_id=zone_id):
        logger.info(f"DNS record {fqdn} already exists")
        return None

    return await client.dns.records.create(
        zone_id=zone_id,
        content=config.k8s_cname,
        type="CNAME",
        name=fqdn,
        ttl=5 * 60,  # 5 minutes
    )


async def delete_dns_record(config: AppSettings, fqdn: str, zone_id: str) -> None:
    """
    Delete a DNS record
    """
    client: AsyncCloudflare = await get_cloudflare_client(config=config)
    records = await client.dns.records.list(zone_id=zone_id, type="CNAME", name=fqdn)

    records = records.model_dump()
    dns_record_id = None
    if records["result"]:
        for record in records["result"]:
            if record["name"] == fqdn:
                dns_record_id = record["id"]
                break
    if dns_record_id:
        await client.dns.records.delete(zone_id=zone_id, dns_record_id=dns_record_id)


async def link_bucket_to_custom_domain(config: AppSettings, bucket_name: str, custom_domain: str, zone_id: str) -> dict:
    """
    Link a bucket to a custom domain
    """
    url_base = f"https://api.cloudflare.com/client/v4/accounts/{config.cloudflare.account_id}/r2/buckets/{bucket_name}/domains/custom"
    headers = {"Authorization": f"Bearer {config.cloudflare.api_token}"}

    list_response = requests.get(url_base, headers=headers, timeout=120)

    if list_response.status_code == 200:
        existing_domains = list_response.json().get("result", {}).get("domains", [])
        existing_hostnames = [domain["domain"] for domain in existing_domains]
        if custom_domain in existing_hostnames:
            logger.info(f"The custom domain {custom_domain} is already associated with the bucket.")
            return

    response = requests.post(
        url=url_base,
        headers=headers,
        json={"domain": custom_domain, "zoneId": zone_id, "enabled": True},
        timeout=120,
    )
    if response.status_code == 200:
        return
    else:
        raise Exception(
            f"Failed to link bucket {bucket_name} to custom domain {custom_domain}. Status Code: {response.status_code}"
        )
