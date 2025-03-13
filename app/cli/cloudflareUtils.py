import asyncio
import hashlib
from datetime import datetime

import aiohttp
from cloudflare import AsyncCloudflare
from cloudflare.types.r2 import TemporaryCredentialCreateResponse
from loguru import logger

from app.cli.temporal.activities.cloudflareSetup import CloudflareBucketCredentials
from app.core.settings import APP_CONFIG, AppSettings, get_settings


def get_cloudflare_sdk_client(config: AppSettings) -> AsyncCloudflare:
    """
    Get a Cloudflare client
    """
    return AsyncCloudflare(api_token=config.cloudflare.api_token)


async def get_async_cloudflare_client() -> aiohttp.ClientSession:
    """
    Get an async HTTP client for Cloudflare API
    """
    _config = get_settings()
    headers = {"Authorization": f"Bearer {_config.cloudflare.api_token}"}
    return aiohttp.ClientSession(
        base_url=_config.cloudflare.api_url, headers=headers, timeout=aiohttp.ClientTimeout(total=120)
    )


async def get_temporary_credentials(config: AppSettings, bucket_name: str) -> TemporaryCredentialCreateResponse:
    """
    Get temporary credentials
    """
    client: AsyncCloudflare = get_cloudflare_sdk_client(config=config)
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
    client: AsyncCloudflare = get_cloudflare_sdk_client(config=config)
    response = await client.r2.buckets.list(account_id=config.cloudflare.account_id, name_contains=bucket_name)
    return response.result.get("buckets", [])


async def create_bucket(config: AppSettings, bucket_name: str, location_hint: str | None = None) -> dict | None:
    """
    Create a bucket
    """
    client: AsyncCloudflare = get_cloudflare_sdk_client(config=config)
    if not await get_bucket(config=config, bucket_name=bucket_name):
        return (
            await client.r2.buckets.create(
                account_id=config.cloudflare.account_id, name=bucket_name, location_hint=location_hint
            )
            if location_hint
            else await client.r2.buckets.create(account_id=config.cloudflare.account_id, name=bucket_name)
        )
    return None


async def delete_bucket(config: AppSettings, bucket_name: str) -> dict:
    """
    Delete a bucket
    """
    client: AsyncCloudflare = get_cloudflare_sdk_client(config=config)
    return await client.r2.buckets.delete(account_id=config.cloudflare.account_id, bucket_name=bucket_name)


async def get_dns_record(config: AppSettings, fqdn: str, zone_id: str) -> list:
    """
    Get a DNS record
    """
    client: AsyncCloudflare = get_cloudflare_sdk_client(config=config)
    response = await client.dns.records.list(zone_id=zone_id, name=fqdn, type="CNAME")
    return response.result


async def create_dns_record(config: AppSettings, fqdn: str, zone_id: str, content: str | None = None) -> dict | None:
    """
    Create a DNS record
    """
    client: AsyncCloudflare = get_cloudflare_sdk_client(config=config)

    # check if the record already exists
    if await get_dns_record(config=config, fqdn=fqdn, zone_id=zone_id):
        logger.info(f"DNS record {fqdn} already exists")
        return None

    return await client.dns.records.create(
        zone_id=zone_id,
        content=content if content else APP_CONFIG.k8s_cname,
        type="CNAME",
        name=fqdn,
        ttl=5 * 60,  # 5 minutes
    )


async def delete_dns_record(config: AppSettings, fqdn: str, zone_id: str) -> None:
    """
    Delete a DNS record
    """
    client: AsyncCloudflare = get_cloudflare_sdk_client(config=config)
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


async def _list_custom_domains(config: AppSettings, bucket_name: str) -> list:
    """
    List custom domains
    """
    async with await get_async_cloudflare_client() as client:
        response = await client.get(
            url=f"accounts/{config.cloudflare.account_id}/r2/buckets/{bucket_name}/domains/custom",
            timeout=aiohttp.ClientTimeout(total=120),
        )
        response.raise_for_status()
        response_json = await response.json()
        return response_json.get("result", {}).get("domains", [])


async def _validate_custom_domain(config: AppSettings, bucket_name: str, custom_domain: str) -> None:
    """
    Validate a custom domain
    """
    count = 0
    step = 5
    timeout = 600
    while True:
        if count > timeout:
            raise TimeoutError(f"DNS propagation check timed out after [10 min]: {custom_domain}")
        domains = await _list_custom_domains(config=config, bucket_name=bucket_name)
        if not domains:
            raise ValueError(f"No domains found for bucket {bucket_name}")
        domain = None
        for _domain in domains:
            if _domain["domain"] == custom_domain:
                domain = _domain
                break

        ownership_status = domain.get("status", {}).get("ownership", "")
        match ownership_status:
            case "active":
                return
            case "pending":
                count += step
                msg = f"Polling for custom domain, '{bucket_name}' bucket has '{ownership_status}' ownership status"
                logger.info(msg)
                await asyncio.sleep(step)
            case _:
                msg = (
                    f"Failed to validate custom domain, '{bucket_name}' bucket has"
                    f"invalid ownership status '{ownership_status}'"
                )
                logger.error(msg)
                raise ValueError(msg)


async def link_bucket_to_custom_domain(config: AppSettings, bucket_name: str, custom_domain: str, zone_id: str) -> dict:
    """
    Link a bucket to a custom domain
    """
    existing_domains: list[dict] = await _list_custom_domains(config=config, bucket_name=bucket_name)

    async with await get_async_cloudflare_client() as client:
        found: bool = False
        for domain in existing_domains:
            if domain["domain"] == custom_domain:
                found = True
                if not domain["enabled"]:
                    response = await client.put(
                        url=f"accounts/{config.cloudflare.account_id}/r2/buckets/{bucket_name}/domains/custom/{custom_domain}",
                        json={"enabled": True},
                    )
                    response.raise_for_status()
                break

        if not found:
            response = await client.post(
                url=f"accounts/{config.cloudflare.account_id}/r2/buckets/{bucket_name}/domains/custom",
                json={"domain": custom_domain, "zoneId": zone_id, "enabled": True},
            )
            response.raise_for_status()

    await _validate_custom_domain(config=config, bucket_name=bucket_name, custom_domain=custom_domain)


async def update_cors_for_bucket(config: AppSettings, bucket_name: str, rules: list) -> None:
    """
    Update CORS for a bucket
    rules: list[dict]
    rules = [{
        "allowed": {
            "methods": ["GET", "PUT", "HEAD", "POST", "DELETE"],
            "origins": ["*"],
            "headers": ["Authorization", "content-type", "x-amz-*", "traceparent"],
        },
        "exposeHeaders": ["ETag", "Location"],
    }]
    """
    async with await get_async_cloudflare_client() as client:
        response = await client.put(
            url=f"accounts/{config.cloudflare.account_id}/r2/buckets/{bucket_name}/cors",
            json={"rules": rules},
        )
        if response.status == 200:
            return
        else:
            raise RuntimeError(f"Failed to update CORS for bucket {bucket_name}")


async def create_cloudflare_bucket_credentials(
    bucket_name: str, config: AppSettings, read_only: bool = False
) -> CloudflareBucketCredentials:
    """
    Create a Cloudflare bucket credentials
    """
    if read_only:
        permission_group_id = config.cloudflare.bucket_read_permission_group_id
        permission_group_name = config.cloudflare.bucket_read_permission_group_name

    else:
        permission_group_id = config.cloudflare.bucket_write_permission_group_id
        permission_group_name = config.cloudflare.bucket_write_permission_group_name
    async with await get_async_cloudflare_client() as client:
        token_list_response = await client.get("user/tokens", params={"per_page": "1000"})

        if token_list_response.status != 200:
            raise RuntimeError(f"Failed to fetch Cloudflare tokens. Status code: {token_list_response.status}")

        token_list = await token_list_response.json()

        selected_token = {}
        for token in token_list["result"]:
            if token["name"] == f"{bucket_name}-app-token" and token["status"] == "active":
                token_issued_on = datetime.fromisoformat(token["issued_on"].replace("Z", "+00:00"))
                if not selected_token:
                    selected_token = token
                    continue
                selected_token_issued_on = datetime.fromisoformat(selected_token["issued_on"].replace("Z", "+00:00"))
                if token_issued_on > selected_token_issued_on:
                    selected_token = token
            if selected_token:
                # need to do manually incase credentials are not found in OnePassword
                return CloudflareBucketCredentials(exists=True)
        response = await client.post(
            url="user/tokens",
            json={
                "name": f"{bucket_name}-app-token",
                "policies": [
                    {
                        "effect": "allow",
                        "resources": {
                            f"com.cloudflare.edge.r2.bucket.{config.cloudflare.account_id}_default_{bucket_name}": "*"
                        },
                        "permission_groups": [{"id": permission_group_id, "name": permission_group_name}],
                    }
                ],
            },
        )

        if response.status != 200:
            raise RuntimeError(
                f"Failed to create Cloudflare bucket credentials for {bucket_name}. Status code: {response.status}"
            )

        response_json = await response.json()
        access_key = response_json["result"]["id"]
        secret_sha_key = response_json["result"]["value"]
        secret_key = hashlib.sha256(secret_sha_key.encode()).hexdigest()

        return CloudflareBucketCredentials(access_key=access_key, secret_key=secret_key, exists=False)
