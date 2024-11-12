from temporalio import activity, workflow
from temporalio.common import RetryPolicy


with workflow.unsafe.imports():
    from datetime import timedelta
    import os
    import orjson
    import requests
    from loguru import logger
    from novu.api import NotificationGroupApi, LayoutApi, IntegrationApi, NotificationTemplateApi, SubscriberApi
    from novu.dto import IntegrationDto, SubscriberDto

    from app.cli.temporal.core.base import Activity
    from app.cli.temporal.penknife import TemplatePath
    from app.cli.temporal.penknife.models.penknifespec import PenknifeSpec
    from app.cli.temporal.core.log import log_info
    from app.core.settings import AppSettings, get_settings
    from app.onepasswordutil import OnePasswordUtil


def get_default_notification_group_id(config: AppSettings, novu_api_key: str) -> str | None:
    """

    :return:
    """
    group_name: str = "General"
    group_client = NotificationGroupApi(url=config.penknife.novu_url, api_key=novu_api_key)
    response = group_client.list()
    for group in response.data:
        if group.name == group_name:
            return group._id
    return None


def get_default_notification_layout_id(config: AppSettings, novu_api_key: str) -> str | None:
    """

    :return:
    """
    layout_name: str = "Default Layout"
    layout_client = LayoutApi(url=config.penknife.novu_url, api_key=novu_api_key)
    response = layout_client.list()
    for layout in response.data:
        if layout.name == layout_name:
            return layout._id
    return None


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
    novu_client = IntegrationApi(url=config.penknife.novu_url, api_key=novu_api_key)
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


def list_integration_provider(config: AppSettings, novu_api_key: str) -> list:
    """
    :return:
    """
    novu_client = IntegrationApi(url=config.penknife.novu_url, api_key=novu_api_key)
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


def set_integration_provider_as_primary(integration_id: str, config: AppSettings, novu_api_key: str) -> None:
    """

    :param integration_id:
    :param config:
    :param novu_api_key:
    :return:
    """
    novu_client: IntegrationApi = IntegrationApi(url=config.penknife.novu_url, api_key=novu_api_key)
    novu_client.set_primary(integration_id)


def add_integration_provider(config: AppSettings, novu_api_key: str) -> None:
    """

    :return:
    """
    provider_data: list = list_integration_provider(config=config, novu_api_key=novu_api_key)
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
                "senderName": "Penknife",
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


def list_novu_notification_template(
    config: AppSettings,
    novu_api_key: str,
    page: int = 0,
    limit: int = 100,
) -> list | None:
    """
    :return:
    """
    novu_client = NotificationTemplateApi(url=config.penknife.novu_url, api_key=novu_api_key)
    response = novu_client.list(page=page, limit=limit)
    template_names: list = [template.to_camel_case().get("name", "") for template in response.data if response]
    return template_names


def create_novu_workflow_templates(template_path: str, config: AppSettings, novu_api_key: str) -> None:
    """

    :param template_path:
    :param config:
    :param api_key:
    :return:
    """
    layout_id: str = get_default_notification_layout_id(config=config, novu_api_key=novu_api_key)
    notification_group_id: str = get_default_notification_group_id(config=config, novu_api_key=novu_api_key)

    template_names: list = list_novu_notification_template(config=config, novu_api_key=novu_api_key)
    template_names: set = set(template_names)
    with open(template_path) as file:
        json_data = file.read()

    data: list[dict] = orjson.loads(json_data)
    for workflow_ in data:
        event_name = workflow_.get("name")
        # check if the workflow with the same name already exists
        if event_name not in template_names:
            workflow_.update({"notificationGroupId": notification_group_id})
            for steps in workflow_.get("steps", []):
                if "layoutId" in steps.get("template", {}):
                    steps["template"].update({"layoutId": layout_id})

            workflow_url = f"{config.penknife.novu_url}/v1/workflows"
            headers: dict = {
                "Authorization": f"ApiKey {novu_api_key}",
                "Content-Type": "application/json",
            }
            response = requests.post(url=workflow_url, headers=headers, json=workflow_, timeout=10)
            if response.status_code >= 400:
                logger.error(f"Failed to create novu workflow template : {response.json()}")


class NovuSetup:
    """
    This class will be used to setup the Novu environment
    """

    def __init__(self: "NovuSetup", penknife: PenknifeSpec) -> None:
        self.penknife: PenknifeSpec = penknife
        self.config: AppSettings = get_settings()

    def get_access_token(self: "NovuSetup") -> str:
        """
        Get the access token for the Novu environment
        """
        url = f"{self.config.penknife.novu_url}/v1/auth/login"

        payload = {"email": self.config.penknife.novu_admin_user, "password": self.config.penknife.novu_admin_password}

        response = requests.post(url=url, json=payload, timeout=120)

        if response.status_code >= 300:
            raise Exception("Failed to get access token for Novu environment")

        return response.json()["data"]["token"]

    def get_organizations_by_name(self: "NovuSetup", organization_name: str, token: str) -> list:
        """
        List the organizations in the Novu environment
        """
        url = f"{self.config.penknife.novu_url}/v1/organizations"

        response = requests.get(url=url, headers={"Authorization": f"Bearer {token}"}, timeout=120)

        if response.status_code >= 300:
            raise Exception(f"Failed to get organization by name: {organization_name}")

        return [row for row in response.json()["data"] if row["name"] == organization_name]

    def create_organization(self: "NovuSetup", token: str, org_name: str) -> dict:
        """
        Create an organization in the Novu environment
        """
        url = f"{self.config.penknife.novu_url}/v1/organizations"

        payload = {
            "name": org_name,
        }

        response = requests.post(url=url, headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=120)

        if response.status_code >= 300:
            raise Exception(f"Failed to create organization: {org_name}")

        return response.json()

    def get_organization_api_key(self: "NovuSetup", token: str) -> str:
        """
        Get the API keys for the organization
        """
        url = f"{self.config.penknife.novu_url}/v1/environments/api-keys"

        response = requests.get(url=url, headers={"Authorization": f"Bearer {token}"}, timeout=120)

        if response.status_code >= 300:
            raise Exception(f"Failed to get API keys for organization status_code:{response.status_code}")

        return response.json()["data"][0]["key"]

    def switch_organization(self: "NovuSetup", organization_id: str, token: str) -> str:
        """
        Switch the organization
        """
        url = f"{self.config.penknife.novu_url}/v1/auth/organizations/{organization_id}/switch"

        response = requests.post(url=url, headers={"Authorization": f"Bearer {token}"}, timeout=120)

        if response.status_code >= 300:
            raise Exception(f"Failed to switch organization: {organization_id}")

        return response.json()["data"]

    def setup_novu(self: "NovuSetup") -> None:
        """
        Setup the Novu environment
        """
        config: AppSettings = get_settings()

        organization_name = f"penknife_{self.penknife.tenant}"
        access_token = self.get_access_token()
        organization = self.get_organizations_by_name(organization_name=organization_name, token=access_token)
        if not organization:
            organization = self.create_organization(token=access_token, org_name=organization_name)
            organization_id = organization["data"]["id"]
        else:
            organization = organization[0]
            organization_id = organization["_id"]

        organization_token = self.switch_organization(organization_id=organization_id, token=access_token)
        api_keys = self.get_organization_api_key(token=organization_token)

        # store in 1Password
        OnePasswordUtil(
            tenant=f"PENKNIFE_{self.penknife.tenant}",
            server_item="application-config",
            vault="Penknife",
        ).insert_if_not_exists(key="novu_api_key", value=api_keys)

        # create the templates
        novu_template_path = os.path.join(TemplatePath, "novu_workflow_template.json")
        create_novu_workflow_templates(template_path=novu_template_path, config=config, novu_api_key=api_keys)

        # add the integration provider
        add_integration_provider(config=config, novu_api_key=api_keys)

        log_info(f"Novu environment setup completed for tenant: {self.penknife.tenant}")

    def create_subscriber_in_novu(self: "NovuSetup", subscriber_id: str) -> str:
        """
        Create subscriber in the new organization
        """
        config: AppSettings = get_settings()

        organization_name = f"penknife_{self.penknife.tenant}"
        access_token = self.get_access_token()
        organization = self.get_organizations_by_name(organization_name=organization_name, token=access_token)

        organization = organization[0]
        organization_id = organization["_id"]

        organization_token = self.switch_organization(organization_id=organization_id, token=access_token)
        api_key = self.get_organization_api_key(token=organization_token)

        novu_client = SubscriberApi(url=config.penknife.novu_url, api_key=api_key)
        subscriber = {
            "subscriber_id": subscriber_id,
            "email": self.penknife.email,
            "first_name": self.penknife.firstName,
            "last_name": self.penknife.lastName,
            "is_online": True,
        }
        subscriber = SubscriberDto(**subscriber)
        novu_client.create(subscriber)


class PenknifeNovuSetupActivity(Activity):
    """
    NovuSetupActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=300)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5, backoff_coefficient=2)

    @staticmethod
    @activity.defn(name="PenknifeNovuSetupActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        NovuSetup(penknife=penknife).setup_novu()
