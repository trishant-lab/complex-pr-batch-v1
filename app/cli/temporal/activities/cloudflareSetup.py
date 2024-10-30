# from cloudflare import AsyncCloudflare
# from temporalio import activity, workflow
# from temporalio.common import RetryPolicy

# from app.cli.cloudflare import get_cloudflare_client
# from app.cli.temporal.core.log import log_error, log_info
# from app.core.settings import AppSettings, get_settings


# with workflow.unsafe.imports_passed_through():
#     import os
#     import requests
#     from datetime import timedelta
#     from app.cli.temporal.core.base import Activity
#     from app.cli.temporal.core.base import LaunchpadCLIBaseModel


# class LinkBucketToDomainActivityModel(LaunchpadCLIBaseModel):
#     """
#     LinkBucketToDomainActivityModel
#     """

#     tenant: str
#     bucket_name: str
#     domain_name: str
#     zone_id: str


# class CloudflareSetupActivity(Activity):
#     """
#     CloudflareSetupActivity
#     """

#     @staticmethod
#     def get_timeout() -> timedelta:
#         """
#         Timeout for the activity
#         """
#         return timedelta(seconds=60)

#     @staticmethod
#     def get_retry_policy() -> RetryPolicy:
#         """
#         RetryPolicy for the activity
#         """
#         return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5, backoff_coefficient=2)

#     @staticmethod
#     @activity.defn(name="LinkBucketToDomainActivity")
#     async def link_bucket_to_domain(activity_input: LinkBucketToDomainActivityModel) -> None:
#         """
#         Link bucket to domain
#         """

#         config: AppSettings = get_settings()

#         client: AsyncCloudflare = await get_cloudflare_client(config=config)

#         # link bucket to domain
#         await client.r2.buckets.create(
#             account_id=config.cloudflare.account_id,
#             bucket=activity_input.bucket_name,
#         )

#         # url = f"https://api.cloudflare.com/client/v4/accounts/{config.cloudflare.account_id}/r2/buckets/{activity_input.bucket_name}/domains/custom"

#         # payload = {
#         #     "domain": f"{activity_input.tenant}.{activity_input.domain_name}",
#         #     "zoneId": activity_input.zone_id
#         # }
#         # headers = {
#         #     "Content-Type": "application/json",
#         #     "cf-r2-jurisdiction": "",
#         #     "Authorization": f"Bearer {config.cloudflare.api_token}"
#         # }

#         # response = requests.request("POST", url, json=payload, headers=headers)

#         # response.raise_for_status()

#         # if response.status_code == 200:
#         #     log_info(f"Bucket {activity_input.bucket_name} linked to domain {activity_input.domain_name}")
#         # else:
#         #     log_error(f"Failed to link bucket {activity_input.bucket_name} to domain {activity_input.domain_name}")
#         #     raise Exception(f"Failed to link bucket
#  {activity_input.bucket_name} to domain {activity_input.domain_name}")


# class CopyArtifactsToBucketActivityModel(LaunchpadCLIBaseModel):
#     """
#     CopyArtifactsToBucketActivityModel
#     """

#     tenant: str
#     bucket_name: str
#     artifact_name: str


# class CopyArtifactsToBucketActivity(Activity):
#     """
#     CopyArtifactsToBucketActivity
#     """

#     @staticmethod
#     def get_timeout() -> timedelta:
#         """
#         Timeout for the activity
#         """
#         return timedelta(seconds=60)

#     @staticmethod
#     def get_retry_policy() -> RetryPolicy:
#         """
#         RetryPolicy for the activity
#         """
#         return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5, backoff_coefficient=2)

#     @staticmethod
#     @activity.defn(name="CopyArtifactsToBucketActivity")
#     async def copy_artifacts_to_bucket(activity_input: CopyArtifactsToBucketActivityModel) -> None:
#         """
#         Copy artifacts to bucket
#         """

#         log_info(f"Copying artifact {activity_input.artifact_name} to bucket {activity_input.bucket_name}")

#         config: AppSettings = get_settings()

#         temporary_credentials = await get_temporary_credentials(config, activity_input.bucket_name)

#         access_key = temporary_credentials["accessKeyId"]
#         secret_key = temporary_credentials["secretAccessKey"]

#         os.system(f"mc alias set {config.cloudflare.s3_alias}
# {config.cloudflare.endpoint} {access_key} {secret_key}")  # nosec

#         os.system(f"mc mirror --remove --overwrite
#  {activity_input.artifact_name} {activity_input.bucket_name}")  # nosec
