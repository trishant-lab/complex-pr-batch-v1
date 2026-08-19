from datetime import timedelta

import aiohttp
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_info, log_error
from app.cli.temporal.dexit.dexit import DexitSpec
from app.core.product_settings.dexit import DexitSettings
from app.core.settings import AppSettings, get_settings
from app.one_password_util import OnePasswordUtil

config: AppSettings = get_settings()
dexit_config: DexitSettings = config.dexit

sinch_subproject_api_url = "https://subproject.api.sinch.com/v1alpha1/"
sinch_fax_api_url = "https://fax.api.sinch.com/v3/"
sinch_account_api_url = "https://account.api.sinch.com/v1/"
sinch_oauth_token_url = "https://auth.sinch.com/oauth2/token"

CONTENT_TYPE_JSON = "application/json"


def sinch_auth_headers(username: str, password: str) -> dict[str, str]:
    """
    Basic auth header for the Sinch APIs.

    aiohttp deprecated the `auth` parameter, so the header is built explicitly.
    """
    return {"Authorization": aiohttp.encode_basic_auth(username, password)}


class FaxSetup:
    def __init__(self: "FaxSetup", dexit: DexitSpec) -> None:
        self.dexit: DexitSpec = dexit
        self.env: str = config.env
        self.server_item = "production-config" if self.env == "production" else "integration-config"
        # Sinch Configuration
        self.sinch_username = dexit_config.sinch_username
        self.sinch_project_id = dexit_config.sinch_project_id
        self.sinch_password = dexit_config.sinch_password
        self.service_name = f"{self.dexit.tenant}_fax_service"
        self.auth_headers = sinch_auth_headers(self.sinch_username, self.sinch_password)

    async def get_sinch_subproject(self) -> dict | None:
        """
        Checks if a Sinch subproject exists for the tenant.
        Returns the subproject details if found, None otherwise.
        """
        async with aiohttp.ClientSession(headers=self.auth_headers) as session:
            url = f"{sinch_subproject_api_url}projects/{self.sinch_project_id}/subprojects"
            response = await session.get(url=url)

            if response.status != 200:
                error_body = await response.text()
                raise aiohttp.ClientError(
                    f"Failed to fetch Sinch subproject: status={response.status}, body={error_body}"
                )

            content = await response.json(content_type=None)

            for subproject in content.get("subprojects", []):
                if subproject.get("displayName") == self.dexit.tenant:
                    return subproject

            return None

    async def create_sinch_subproject(self) -> dict:
        """
        Creates a new Sinch subproject for the tenant.
        """
        payload = {"displayName": self.dexit.tenant}

        async with aiohttp.ClientSession(headers=self.auth_headers) as session:
            url = f"{sinch_subproject_api_url}projects/{self.sinch_project_id}/subprojects"
            response = await session.post(url=url, json=payload, headers={"Content-Type": CONTENT_TYPE_JSON})

            if response.status != 200:
                error_body = await response.text()
                raise aiohttp.ClientError(
                    f"Failed to create Sinch subproject: status={response.status}, body={error_body}"
                )

            return await response.json(content_type=None)

    async def fax_request(self: "FaxSetup", url: str, payload: dict, username: str, password: str) -> tuple[dict, int]:
        """
        Sends a fax API request asynchronously.
        :param url: The URL of the API endpoint.
        :param payload: The payload to be sent with the request.
        :return: The API response.
        """
        async with aiohttp.ClientSession(headers=sinch_auth_headers(username, password)) as session:
            response = await session.post(url=url, data=payload)
            content = await response.json(content_type=None)
            status = response.status

        return content, status

    async def get_fax_service(self: "FaxSetup", subproject_id: str) -> dict | None:
        """
        Return the tenant's fax service if it already exists.
        """
        async with aiohttp.ClientSession(headers=self.auth_headers) as session:
            url = f"{sinch_fax_api_url}projects/{subproject_id}/services"
            response = await session.get(url=url)

            if response.status != 200:
                error_body = await response.text()
                raise aiohttp.ClientError(
                    f"Failed to list Sinch fax services: status={response.status}, body={error_body}"
                )

            content = await response.json(content_type=None)

        for service in content.get("services", []):
            if service.get("name") == self.service_name:
                return service

        return None

    async def create_fax_service(self: "FaxSetup", subproject_id: str, webhook_secret: str) -> dict:
        """
        Create the tenant's fax service, pointed at that tenant's fax worker.
        """
        payload = {
            "name": self.service_name,
            "incomingWebhookUrl": (
                f"https://{self.dexit.tenant}.{dexit_config.domain_name}"
                f"/worker/receive/receive-fax?webhookSecret={webhook_secret}"
            ),
            "webhookContentType": CONTENT_TYPE_JSON,
            "inProgressNotifications": True,
            # inbound faxes fall back to the project default when a number is not bound
            # to a service, and this is the only service in the tenant's subproject
            "defaultForProject": True,
        }

        async with aiohttp.ClientSession(headers=self.auth_headers) as session:
            url = f"{sinch_fax_api_url}projects/{subproject_id}/services"
            response = await session.post(url=url, json=payload)

            if response.status != 201:
                error_body = await response.text()
                raise aiohttp.ClientError(
                    f"Failed to create Sinch fax service: status={response.status}, body={error_body}"
                )

            return await response.json(content_type=None)

    async def setup_fax(self: "FaxSetup") -> str:
        """
        Setup fax API.

        Every resource is reconciled on its own rather than behind a single
        "subproject already exists" check -- an attempt that dies partway (the access
        key call needs a permission the subproject call does not) has to be repairable
        by re-running, instead of being skipped and reported as success.
        """
        one_password = OnePasswordUtil(
            tenant=self.dexit.tenant,
            server_item=self.server_item,
            vault="Dexit",
        )

        subproject = await self.get_sinch_subproject()
        if subproject:
            log_info(f"Sinch subproject for tenant {self.dexit.tenant} already exists, using existing subproject")
        else:
            subproject = await self.create_sinch_subproject()

        subproject_id = subproject["subprojectId"]
        await one_password.insert_if_not_exists(key="sinch_project_id", value=subproject_id)

        service = await self.get_fax_service(subproject_id=subproject_id)
        if service:
            log_info(f"Sinch fax service for tenant {self.dexit.tenant} already exists, using existing service")
        else:
            webhook_secret = await one_password.get_key("webhook_secret")
            if not webhook_secret:
                raise ValueError(
                    f"webhook_secret is not set in 1Password for tenant {self.dexit.tenant}; "
                    "the onboarding workflow stores it before this activity runs"
                )
            service = await self.create_fax_service(subproject_id=subproject_id, webhook_secret=webhook_secret)

        await one_password.insert_if_not_exists(key="sinch_fax_service_id", value=service["id"])

        # Generate the tenant's own Sinch access key + secret and store them in 1Password.
        # Last, and non-fatal: the Access Keys management API currently denies this
        # account's key, and the tenant is otherwise fully provisioned, so the failure is
        # logged instead of failing onboarding. Re-running fills the keys in once the
        # permission exists, because every step above reconciles.
        if not await one_password.get_key("sinch_access_key"):
            try:
                access_key = await self.create_sinch_access_key(subproject_id=subproject_id)
            except aiohttp.ClientError as e:
                log_error(f"Sinch access key not created for tenant {self.dexit.tenant}: {e}")
            else:
                await one_password.insert_if_not_exists(key="sinch_access_key", value=access_key["id"])
                await one_password.insert_if_not_exists(key="sinch_access_key_secret", value=access_key["secret"])

        log_info(f"Fax setup completed for tenant: {self.dexit.tenant}")
        return subproject_id

    async def get_sinch_access_token(self: "FaxSetup") -> str:
        """
        Exchange the configured key id + secret for a short-lived OAuth bearer token.
        """
        async with aiohttp.ClientSession(headers=self.auth_headers) as session:
            response = await session.post(url=sinch_oauth_token_url, data={"grant_type": "client_credentials"})

            if response.status != 200:
                error_body = await response.text()
                raise aiohttp.ClientError(
                    f"Failed to obtain Sinch access token: status={response.status}, body={error_body}"
                )

            content = await response.json(content_type=None)

        return content["access_token"]

    async def create_sinch_access_key(self: "FaxSetup", subproject_id: str) -> dict:
        """
        Create a Sinch access key + secret for the subproject.
        Returns a dict with `id` (access key) and `secret` (access secret key).

        The Access Keys management API is a separate host from the fax and subproject
        APIs and takes a bearer token rather than basic auth. Sinch documents two hosts
        for it -- account.api in the getting started guide, accesskey.api in the API
        reference -- which behave identically.
        """
        token = await self.get_sinch_access_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": CONTENT_TYPE_JSON}

        async with aiohttp.ClientSession(headers=headers) as session:
            url = f"{sinch_account_api_url}projects/{subproject_id}/accessKeys"
            response = await session.post(url=url, json={"displayName": f"{self.dexit.tenant}-launchpad"})

            if response.status not in (200, 201):
                error_body = await response.text()
                raise aiohttp.ClientError(
                    f"Failed to create Sinch access key: status={response.status}, body={error_body}"
                )

            content = await response.json(content_type=None)

        # The key is nested under "accessKey"; the secret sits alongside it and is only
        # ever returned here, on creation.
        return {"id": content["accessKey"]["accessKeyId"], "secret": content["secret"]}


class FaxSetupActivity(Activity):
    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=120)

    @staticmethod
    @activity.defn(name="fax_setup_activity")
    async def defn(dexit: DexitSpec) -> None:
        """
        Callable for the activity
        """
        # Setup fax
        await FaxSetup(dexit=dexit).setup_fax()


class DeleteSinchSubprojectActivityModel(LaunchpadCLIBaseModel):
    """
    Model for DeleteSinchSubprojectActivity
    """

    tenant: str
    server_item: str


class DeleteSinchSubprojectActivity(Activity):
    """
    Activity to delete a Sinch Subproject
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="DeleteSinchSubprojectActivity")
    async def defn(activity_model: DeleteSinchSubprojectActivityModel) -> None:
        """
        Delete a Sinch Subproject by retrieving subproject ID from 1Password
        """
        one_password = OnePasswordUtil(
            tenant=activity_model.tenant,
            server_item=activity_model.server_item,
            vault="Dexit",
        )
        subproject_id = await one_password.get_key("sinch_project_id")
        if not subproject_id:
            log_info(f"Sinch subproject ID not found for tenant: {activity_model.tenant}")
            return

        auth_headers = sinch_auth_headers(dexit_config.sinch_username, dexit_config.sinch_password)
        async with aiohttp.ClientSession(headers=auth_headers) as session:
            url = f"{sinch_subproject_api_url}subprojects/{subproject_id}"
            try:
                response = await session.delete(url=url)

                if response.status == 404:
                    log_info(f"Sinch subproject not found for tenant: {activity_model.tenant}")
                    return

                if response.status != 200:
                    content = await response.text()
                    log_error(
                        f"Failed to delete Sinch subproject for tenant {activity_model.tenant}: "
                        f"status={response.status}, body={content}"
                    )
                    return

                log_info(f"Sinch subproject deleted successfully for tenant: {activity_model.tenant}")

            except aiohttp.ClientError as e:
                log_error(f"Failed to delete Sinch subproject: {e}")
                raise e
