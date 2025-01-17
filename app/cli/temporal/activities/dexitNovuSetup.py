import os
from datetime import timedelta

import orjson
import aiohttp
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity
from app.cli.temporal.core.log import log_info
from novu.api import NotificationGroupApi, IntegrationApi, NotificationTemplateApi
from novu.dto import IntegrationDto

from app.cli.temporal.dexit import TemplatePath
from app.cli.temporal.dexit.dexit import DexitSpec
from app.core.settings import AppSettings, get_settings
from app.onepasswordutil import OnePasswordUtil
from app.template_env import get_env


def get_notification_group_id(group_name: str, config: AppSettings, api_key: str) -> None | str:
    """

    :param group_name:
    :param config:
    :param api_key:
    :return:
    """
    group_client = NotificationGroupApi(url=config.dexit.novu_url, api_key=api_key)
    response = group_client.list()
    for group in response.data:
        if group.to_camel_case().get("name", "") == group_name:
            return group.to_camel_case().get("_id")
    return None


def get_novu_notification_workflow_by_name(
    workflow_name: str,
    config: AppSettings,
    api_key: str,
    page: int = 0,
    limit: int = 100,
) -> None | dict:
    """

    :param workflow_name:
    :param config:
    :param page:
    :param limit:
    :param api_key:
    :return:
    """
    novu_client = NotificationTemplateApi(url=config.dexit.novu_url, api_key=api_key)
    response = novu_client.list(page=page, limit=limit)
    for template in response.data:
        if template.to_camel_case().get("name") == workflow_name:
            return template.to_camel_case()
    return None


async def create_novu_notification_workflow(data: dict, config: AppSettings, api_key: str) -> None:
    """
    :param data:
    :param config:
    :param api_key:
    :return:
    """
    workflow = get_novu_notification_workflow_by_name(workflow_name=data["name"], config=config, api_key=api_key)
    headers: dict = {
        "Authorization": f"ApiKey {api_key}",
        "Content-Type": "application/json",
    }
    url: str = f"{config.dexit.novu_url}/v1/workflows"
    if not workflow:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data, timeout=10) as response:
                if response.status >= 400:
                    raise RuntimeError(f"Failed to create novu workflow template : {response.json()}")


async def create_novu_workflow_templates(target_dir: str, config: AppSettings, api_key: str) -> None:
    """

    :param target_dir:
    :param config:
    :param api_key:
    :return:
    """
    id_ = get_notification_group_id(group_name="General", config=config, api_key=api_key)
    notification = {"notification_grp_id": id_}
    for _root, _dirs, files in os.walk(target_dir):
        for file in files:
            template_env = get_env(template_path=target_dir)
            jinja_template = template_env.get_template(file)

            rendered_template = jinja_template.render(notification=notification)
            rendered_template = orjson.loads(rendered_template)

            await create_novu_notification_workflow(data=rendered_template, config=config, api_key=api_key)


def list_integration_provider(config: AppSettings, novu_api_key: str) -> list:
    """
    :return:
    """
    novu_client = IntegrationApi(url=config.dexit.novu_url, api_key=novu_api_key)
    response = novu_client.list()
    return [
        {
            "id": res._id,
            "provider": res.provider_id,
            "channel": res.channel,
            "active": res.active,
        }
        for res in response
    ]


def integrate_provider(
    provider: str,
    channel: str,
    credentials: dict,
    config: AppSettings,
    novu_api_key: str,
    active: bool = True,
) -> str:
    """
    :return:
    """
    novu_client = IntegrationApi(url=config.dexit.novu_url, api_key=novu_api_key)
    integration = {
        "provider_id": provider,
        "channel": channel,
        "credentials": credentials,
        "active": active,
    }
    integration = IntegrationDto(**integration)

    res = novu_client.create(
        integration=integration,
    )
    return res._id


def set_integration_provider_as_primary(integration_id: str, config: AppSettings, novu_api_key: str) -> None:
    """
    :param integration_id:
    :param config:
    :param novu_api_key:
    :return:
    """
    novu_client: IntegrationApi = IntegrationApi(url=config.jeeves.novu_url, api_key=novu_api_key)
    novu_client.set_primary(integration_id)


def add_integration_provider(config: AppSettings, novu_api_key: str) -> None:
    """

    :return:
    """
    provider_data: list = list_integration_provider(config=config, novu_api_key=novu_api_key)
    # chat_exist: bool = False
    email_exist: bool = False
    in_app_exist: bool = False
    for item in provider_data:
        if item.get("channel", "") == "email":
            email_exist = True
        if item.get("channel", "") == "in_app":
            in_app_exist = True

    # adding email provider sendgrid
    if not email_exist:
        integration_id = integrate_provider(
            provider="sendgrid",
            channel="email",
            credentials={
                "apiKey": config.sendgrid.api_key,
                "from": "developer@314ecorp.com",
                "senderName": "Dexit",
            },
            active=True,
            config=config,
            novu_api_key=novu_api_key,
        )

        if integration_id:
            set_integration_provider_as_primary(integration_id=integration_id, config=config, novu_api_key=novu_api_key)

    # adding in app provider novu
    if not in_app_exist:
        integrate_provider(
            provider="novu", channel="in_app", credentials={}, active=True, config=config, novu_api_key=novu_api_key
        )


class NovuSetup:
    """
    This class will be used to setup the Novu environment
    """

    def __init__(self: "NovuSetup", dexit: DexitSpec) -> None:
        self.dexit: DexitSpec = dexit
        self.config: AppSettings = get_settings()

    async def get_access_token(self: "NovuSetup") -> str:
        """
        Get the access token for the Novu environment
        """
        url = f"{self.config.dexit.novu_url}/v1/auth/login"

        payload = {"email": self.config.dexit.novu_admin_user, "password": self.config.dexit.novu_admin_password}

        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, json=payload, timeout=120) as response:
                if response.status >= 400:
                    raise aiohttp.ClientResponseError(
                        f"Failed to get access token for Novu environment, status_code: {response.status}",
                        request=response.request,
                        response=response,
                    )

        if response.status_code >= 300:
            raise aiohttp.ClientResponseError(
                f"Failed to get access token for Novu environment, status_code: {response.status_code}",
                request=response.request,
                response=response,
            )

        return response.json()["data"]["token"]

    async def get_organizations_by_name(self: "NovuSetup", organization_name: str, token: str) -> list:
        """
        List the organizations in the Novu environment
        """
        url = f"{self.config.dexit.novu_url}/v1/organizations"

        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers={"Authorization": f"Bearer {token}"}, timeout=120) as response:
                if response.status >= 400:
                    raise RuntimeError(f"Failed to get organization by name: {organization_name}")

        if response.status_code >= 300:
            raise RuntimeError(f"Failed to get organization by name: {organization_name}")

        return [row for row in response.json()["data"] if row["name"] == organization_name]

    async def create_organization(self: "NovuSetup", token: str, org_name: str) -> dict:
        """
        Create an organization in the Novu environment
        """
        url = f"{self.config.dexit.novu_url}/v1/organizations"

        payload = {
            "name": org_name,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=url, headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=120
            ) as response:
                if response.status >= 400:
                    raise RuntimeError(f"Failed to create organization: {org_name}")

        if response.status_code >= 300:
            raise RuntimeError(f"Failed to create organization: {org_name}")

        return response.json()

    async def get_organization_api_key(self: "NovuSetup", token: str) -> str:
        """
        Get the API keys for the organization
        """
        url = f"{self.config.dexit.novu_url}/v1/environments/api-keys"

        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers={"Authorization": f"Bearer {token}"}, timeout=120) as response:
                if response.status >= 400:
                    raise RuntimeError(f"Failed to get API keys for organization status_code:{response.status}")

        if response.status_code >= 300:
            raise RuntimeError(f"Failed to get API keys for organization status_code:{response.status_code}")

        return response.json()["data"][0]["key"]

    async def switch_organization(self: "NovuSetup", organization_id: str, token: str) -> str:
        """
        Switch the organization
        """
        url = f"{self.config.dexit.novu_url}/v1/auth/organizations/{organization_id}/switch"

        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, headers={"Authorization": f"Bearer {token}"}, timeout=120) as response:
                if response.status >= 400:
                    raise RuntimeError(f"Failed to switch organization: {organization_id}")

        if response.status_code >= 300:
            raise RuntimeError(f"Failed to switch organization: {organization_id}")

        return response.json()["data"]

    async def setup_novu(self: "NovuSetup") -> None:
        """
        Setup the Novu environment
        """
        config: AppSettings = get_settings()
        env: str = config.env
        server_item = "production-config" if env == "production" else "integration-config"

        organization_name = f"dexit_{self.dexit.tenant}"
        access_token = await self.get_access_token()
        organization = await self.get_organizations_by_name(organization_name=organization_name, token=access_token)
        if not organization:
            organization = await self.create_organization(token=access_token, org_name=organization_name)
            organization_id = organization["data"]["id"]
        else:
            organization = organization[0]
            organization_id = organization["_id"]

        log_info(f"Novu Organization {organization_name} created successfully.")

        organization_token = await self.switch_organization(organization_id=organization_id, token=access_token)
        api_keys = await self.get_organization_api_key(token=organization_token)

        # store in 1Password
        OnePasswordUtil(
            tenant=self.dexit.tenant,
            server_item=server_item,
            vault="Dexit",
        ).insert_if_not_exists(key="novu_api_key", value=api_keys)

        # create the templates
        novu_template_path = os.path.join(TemplatePath, "novu_workflow_template")
        await create_novu_workflow_templates(target_dir=novu_template_path, config=config, api_key=api_keys)

        log_info("Novu Workflow templates created successfully.")

        # add the integration provider
        add_integration_provider(config=config, novu_api_key=api_keys)

        log_info("Integration provider added successfully.")


class DexitNovuSetupActivity(Activity):
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
    @activity.defn(name="novu_setup_activity")
    async def defn(dexit: DexitSpec) -> None:
        """
        Callable for the activity
        """
        # Setup novu
        dexit_novu_setup = NovuSetup(dexit=dexit)
        await dexit_novu_setup.setup_novu()
