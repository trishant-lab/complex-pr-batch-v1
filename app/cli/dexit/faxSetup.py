import aiohttp

from app.cli.dexit.dexit import DexitSpec
from app.onepasswordutil import OnePasswordUtil
from app.core.settings import AppSettings, get_settings


class FaxSetup:
    def __init__(self, dexit: DexitSpec) -> None:
        self.dexit: DexitSpec = dexit
        self.config: AppSettings = get_settings()
        self.env: str = self.config.env
        self.domain_name = "com" if self.env == "production" else "tech"

    async def fax_request(self, url: str, payload: dict):
        """
        Sends a fax API request asynchronously.
        :param url: The URL of the API endpoint.
        :param payload: The payload to be sent with the request.
        :return: The API response.
        """
        username = self.config.dexit.FaxAccountId
        password = self.config.dexit.FaxApiToken
        async with aiohttp.ClientSession() as session:
            response = await session.post(
                url=url,
                auth=aiohttp.BasicAuth(username, password),
                data=payload)
            content = await response.json()
            status = response.status

        return content, status

    async def setup_fax(self):
        endpoint = f"https://{self.dexit.tenant}.dexit.314ecorp.{self.domain_name}/public/api/v1/fax/receiveFax"

        contents = f'<?xml version="1.0" encoding="UTF-8"?>\n<Response>\n' \
                   f'<Receive action="{endpoint}" mediaType="application/pdf"/>\n' \
                   f'</Response>'

        payload = {
            "Name": f"314e_{self.env}_{self.dexit.tenant}",
            "Contents": contents
        }

        try:
            content, status = await self.fax_request(
                url=self.config.dexit.LamlUrl,
                payload=payload
            )
            if status != 201 and status != 422:
                raise Exception(f'API createLamlBin failed with status code : {status}')
            elif status == 422:
                raise Exception(f"API createLamlBin Error '{content['message']}'")

            # store in 1Password
            OnePasswordUtil(
                tenant=f"Dexit_Server_{self.dexit.tenant}",
                server_item="application-config",
                vault="Dexit",
            ).insert_if_not_exists(key="fax_url", value=content['request_url'])

            return content
        except Exception as e:
            raise Exception(f'laml bin creation failed with error : {e}')
