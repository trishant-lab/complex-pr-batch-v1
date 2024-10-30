# import os
# import asyncio
# from cloudflare import AsyncCloudflare

# from app.core.settings import AppSettings


# async def get_cloudflare_client(config: AppSettings) -> AsyncCloudflare:
#     return AsyncCloudflare(api_token=config.cloudflare.api_token)


# async def get_temporary_credentials(config: AppSettings, bucket_name: str) -> dict:
#     """
#     Get temporary credentials
#     """

#     client: AsyncCloudflare = await get_cloudflare_client(config=config)
#     return await client.r2.temporary_credentials.create(
#         account_id=config.cloudflare.account_id,
#         bucket=bucket_name,
#         parent_access_key_id=config.cloudflare.access_key,
#         permission="object-read-write",
#         ttl_seconds=5 * 60,
#     )
