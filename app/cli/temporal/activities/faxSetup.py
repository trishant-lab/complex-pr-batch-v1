from datetime import timedelta

import aiohttp
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity
from app.cli.temporal.dexit.dexit import DexitSpec
from app.cli.temporal.core.log import log_info
from app.onepasswordutil import OnePasswordUtil
from app.core.settings import AppSettings, get_settings


class FaxSetup:
    def __init__(self: "FaxSetup", dexit: DexitSpec) -> None:
        self.dexit: DexitSpec = dexit
        self.config: AppSettings = get_settings()
        self.env: str = self.config.env
        self.server_item = "production-config" if self.env == "production" else "integration-config"
        # SignalWire API base URL
        self.signalwire_space = "314e"
        self.signalwire_url = f"https://{self.signalwire_space}.signalwire.com/api/laml/2010-04-01"
        self.account_sid = self.config.dexit.FaxAccountId
        self.auth_token = self.config.dexit.FaxApiToken

    async def create_signalwire_subaccount(self) -> dict:
        """
        Creates a new SignalWire subaccount for the tenant.
        """
        payload = {"FriendlyName": self.dexit.tenant}

        async with aiohttp.ClientSession() as session:
            url = f"{self.signalwire_url}/Accounts"
            response = await session.post(
                url=url, auth=aiohttp.BasicAuth(self.account_sid, self.auth_token), data=payload
            )

            if response.status == 404:
                raise aiohttp.ClientError(f"API endpoint not found. URL: {url}")

            content = await response.json()
            if response.status != 201:
                raise aiohttp.ClientError(f"Failed to create SignalWire subaccount: {content}")
            return content

    async def create_sub_account_token(self, subproject_id: str) -> dict:
        """
        Creates a new SignalWire subaccount token for the tenant.
        """
        url = f"{self.signalwire_url}/Accounts/{self.account_sid}/tokens"

        payload = {
            "name": self.dexit.tenant,
            "permissions": ["fax", "numbers", "management"],
            "subproject_id": subproject_id,
        }

        async with aiohttp.ClientSession() as session:
            response = await session.post(
                url=url, auth=aiohttp.BasicAuth(self.account_sid, self.auth_token), json=payload
            )

            if response.status == 404:
                raise aiohttp.ClientError(f"API endpoint not found. URL: {url}")

            content = await response.json()
            if response.status != 200:
                raise aiohttp.ClientError(f"Failed to create SignalWire subaccount token: {content}")
            return content

    async def fax_request(self: "FaxSetup", url: str, payload: dict, username: str, password: str) -> tuple[dict, int]:
        """
        Sends a fax API request asynchronously.
        :param url: The URL of the API endpoint.
        :param payload: The payload to be sent with the request.
        :return: The API response.
        """
        async with aiohttp.ClientSession() as session:
            response = await session.post(url=url, auth=aiohttp.BasicAuth(username, password), data=payload)
            content = await response.json()
            status = response.status

        return content, status

    async def setup_fax(self: "FaxSetup") -> dict:
        """
        Setup fax API.
        """
        # Create SignalWire subaccount
        subaccount = await self.create_signalwire_subaccount()
        subaccount_token = await self.create_sub_account_token(subaccount["sid"])

        # Store credentials in 1Password
        one_password = OnePasswordUtil(
            tenant=self.dexit.tenant,
            server_item=self.server_item,
            vault="Dexit",
        )
        one_password.insert_if_not_exists(key="fax_account_id", value=subaccount["sid"])
        one_password.insert_if_not_exists(key="fax_api_token", value=subaccount_token["token"])

        # Set up LaML bin with new credentials
        self.laml_url = f"https://314e.signalwire.com/api/laml/2010-04-01/Accounts/{subaccount['sid']}/LamlBins"
        self.endpoint = f"https://{self.dexit.tenant}.api.{self.config.dexit.domain_name}/public/api/v1/fax/receiveFax"

        contents = (
            f'<?xml version="1.0" encoding="UTF-8"?>\n<Response>\n'
            f'<Receive action="{self.endpoint}" mediaType="application/pdf"/>\n'
            f"</Response>"
        )

        payload = {"Name": f"314e_{self.env}_{self.dexit.tenant}", "Contents": contents}

        content, status = await self.fax_request(
            url=self.laml_url, payload=payload, username=subaccount["sid"], password=subaccount_token["token"]
        )
        if status != 201 and status != 422:
            raise aiohttp.ClientError(f"API createLamlBin failed with status code : {status}")
        elif status == 422:
            raise aiohttp.ClientError(f"API createLamlBin Error '{content['message']}'")

        # store in 1Password
        one_password.insert_if_not_exists(key="fax_url", value=content["request_url"])

        log_info(f"Fax setup completed for tenant: {self.dexit.tenant}")

        return content


class FaxSetupActivity(Activity):
    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=1,
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
