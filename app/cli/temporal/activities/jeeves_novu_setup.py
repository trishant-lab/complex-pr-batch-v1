import asyncio
from datetime import timedelta

import aiohttp
import httpx
from loguru import logger
from novu.api import IntegrationApi, LayoutApi, NotificationGroupApi, NotificationTemplateApi
from novu.dto import IntegrationDto
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity
from app.cli.temporal.core.log import log_info
from app.cli.temporal.jeeves.jeeves import JeevesSpec
from app.cli.temporal.jeeves.template_main import (
    get_account_created_custom_email,
    get_asset_created_custom_email,
    get_asset_deleted_custom_email,
    get_asset_expired_custom_email,
    get_asset_expiring_in_1_day_custom_email,
    get_asset_expiring_in_7_days_custom_email,
    get_asset_expiring_in_30_days_custom_email,
    get_asset_published_custom_email,
    get_asset_updated_custom_email,
    get_assignment_assigned_custom_email,
    get_assignment_created_custom_email,
    get_assignment_due_in_1_day_custom_email,
    get_assignment_due_in_7_days_custom_email,
    get_assignment_due_in_15_days_custom_email,
    get_assignment_overdue_custom_email,
    get_assignment_updated_custom_email,
    get_feedback_created_custom_email,
    get_layout_content,
    get_review_comment_added_custom_email,
)
from app.core.settings import AppSettings, get_settings
from app.one_password_util import OnePasswordUtil


def get_default_notification_group_id(config: AppSettings, novu_api_key: str) -> str | None:
    """

    :return:
    """
    group_name: str = "General"
    group_client = NotificationGroupApi(url=config.jeeves.novu_url, api_key=novu_api_key)
    response = group_client.list()
    for group in response.data:
        if group.name == group_name:
            return group._id
    return None


def get_default_notification_layout_id(
    config: AppSettings,
    novu_api_key: str,
    layout_name: str = "Jeeves Layout",
) -> str | None:
    """

    :return:
    """
    layout_client = LayoutApi(url=config.jeeves.novu_url, api_key=novu_api_key)
    response = layout_client.list()
    for layout in response.data:
        if layout.name == layout_name:
            return layout._id
    return None


async def create_novu_notification_layout(
    config: AppSettings,
    novu_api_key: str,
    layout_name: str,
    layout_content: str,
    is_default: str = False,
) -> int | None:
    """
    create novu notification layout
    :param config:
    :param novu_api_key:
    :param layout_name:
    :param layout_content:
    :param is_default:
    :return:
    """
    headers: dict = {
        "Authorization": f"ApiKey {novu_api_key}",
        "Content-Type": "application/json",  # NOSONAR
    }
    data: dict = {
        "name": layout_name,
        "identifier": layout_name.lower().replace(" ", "-"),
        "description": layout_name,
        "content": layout_content,
        "isDefault": is_default,
    }
    async with aiohttp.ClientSession() as session:
        response = await session.post(
            url=f"{config.jeeves.novu_url}/v1/layouts",
            json=data,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=60),
        )
        response_json = await response.json()
        if response.status >= 400:
            logger.error(f"Failed to create novu layout : {response_json}")
    return response.status


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
    novu_client = IntegrationApi(url=config.jeeves.novu_url, api_key=novu_api_key)
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


async def create_novu_workflow_template(
    event_name: str,
    custom_email: str,
    email_subject: str,
    chat_content: str,
    inapp_content: str,
    config: AppSettings,
    novu_api_key: str,
    digest_amount: int = 5,
    digest: bool = True,
    in_app_redirect_url: str = "",
) -> int:
    """
    create novu workflow template
    :param event_name:
    :param custom_email:
    :param email_subject:
    :param chat_content:
    :param inapp_content:
    :param config:
    :param novu_api_key:
    :param digest_amount:
    :param digest:
    :param in_app_redirect_url:
    :return:
    """
    layout_id: str = get_default_notification_layout_id(config=config, novu_api_key=novu_api_key)
    notification_group: str = get_default_notification_group_id(config=config, novu_api_key=novu_api_key)
    digest_step: dict = {
        "name": "Digest",
        "active": True,
        "shouldStopOnFail": False,
        "filters": [],
        "template": {
            "content": "",
            "subject": "",
            "type": "digest",
            "contentType": "editor",
        },
        "metadata": {
            "type": "regular",
            "amount": digest_amount,
            "unit": "minutes",
            "backoff": False,
        },
    }

    email_step: dict = {
        "name": "Email",
        "active": True,
        "shouldStopOnFail": False,
        "replyCallback": {
            "active": False,
        },
        "template": {
            "content": custom_email,
            "subject": email_subject,
            "layoutId": layout_id,
            "senderName": "",
            "type": "email",
            "contentType": "customHtml",
        },
    }

    in_app_step: dict = {
        "name": "In-App",
        "active": True,
        "shouldStopOnFail": False,
        "template": {
            "content": inapp_content,
            "subject": "",
            "type": "in_app",
            "contentType": "editor",
        },
    }

    if in_app_redirect_url:
        in_app_step["template"]["cta"] = {"data": {"url": in_app_redirect_url}, "type": "redirect", "action": {}}

    chat_step: dict = {
        "name": "Chat",
        "active": True,
        "shouldStopOnFail": False,
        "template": {
            "content": chat_content,
            "subject": "",
            "type": "chat",
            "contentType": "editor",
        },
    }

    data: dict = {
        "name": event_name,
        "notificationGroupId": notification_group,
        "active": True,
        "steps": [],
    }
    if digest:
        data["steps"].append(digest_step)
    data["steps"].append(email_step)
    data["steps"].append(in_app_step)
    data["steps"].append(chat_step)
    headers: dict = {
        "Authorization": f"ApiKey {novu_api_key}",
        "Content-Type": "application/json",
    }
    url: str = f"{config.jeeves.novu_url}/v1/workflows"
    async with aiohttp.ClientSession() as session:
        response = await session.post(url, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=10))
        if response.status >= 400:
            logger.error(f"Failed to create novu workflow template : {response.json()}")
    return response.status


def get_novu_notification_template(
    config: AppSettings,
    novu_api_key: str,
    page: int = 0,
    limit: int = 100,
) -> set | None:
    """
    :return:
    """
    novu_client = NotificationTemplateApi(url=config.jeeves.novu_url, api_key=novu_api_key)
    response = novu_client.list(page=page, limit=limit)
    template_names: list = [template.to_camel_case().get("name", "") for template in response.data if response]
    return set(template_names)


async def add_novu_templates(config: AppSettings, novu_api_key: str) -> None:
    """

    :param config:
    :param novu_api_key:
    :return:
    """
    template_names: set = get_novu_notification_template(config=config, novu_api_key=novu_api_key)
    jeeves_layout: str | None = get_default_notification_layout_id(config=config, novu_api_key=novu_api_key)
    if jeeves_layout is None:
        layout_content = await get_layout_content()
        await create_novu_notification_layout(
            config=config,
            novu_api_key=novu_api_key,
            layout_name="Jeeves Layout",
            layout_content=layout_content,
        )

    template_definitions: list[dict] = [
        {
            "event_name": "jeeves-assignment-created",
            "custom_email": await get_assignment_created_custom_email,
            "email_subject": "Assignments are created in Jeeves",
            "chat_content": (
                "Assignments are created in Jeeves.\n{{#each step.events}}\n"
                "Assignment title : {{assignment.name}}.\nClick here: {{assignment.link}}\n\n{{/each}}"
            ),
            "inapp_content": (
                "Assignments are created in Jeeves.\n<br />\n{{#each step.events}}\n"
                "Assignment title : {{assignment.name}}.\nDue on: {{assignment.duedate}}\n<br />\n{{/each}}"
            ),
            "config": config,
            "novu_api_key": novu_api_key,
        },
        {
            "event_name": "jeeves-assignment-updated",
            "custom_email": await get_assignment_updated_custom_email,
            "email_subject": "Assignments are updated in Jeeves",
            "chat_content": (
                "Assignments are updated in Jeeves.\n{{#each step.events}}\n"
                "Assignment title : {{assignment.name}}.\nClick here: {{assignment.link}}\n\n{{/each}}"
            ),
            "inapp_content": (
                "Assignments are updated in Jeeves.\n<br />\n{{#each step.events}}\n"
                "Assignment title : {{assignment.name}}.\nDue on: {{assignment.duedate}}\n<br />\n{{/each}}"
            ),
            "config": config,
            "novu_api_key": novu_api_key,
        },
        {
            "event_name": "jeeves-asset-created",
            "custom_email": await get_asset_created_custom_email,
            "email_subject": "New Assets created in Jeeves",
            "chat_content": (
                "New assets are created.\n\n{{#each step.events}}\n"
                "Asset title:  {{asset.asset_title}} \nClick to View: {{asset.asset_link}}\n\n{{/each}}"
            ),
            "inapp_content": (
                "New assets are created.\n<br />\n{{#each step.events}}\n"
                "Asset title:  {{asset.asset_title}} \n<br />\n{{/each}}"
            ),
            "config": config,
            "novu_api_key": novu_api_key,
        },
        {
            "event_name": "jeeves-assignment-due-in-15-days",
            "custom_email": await get_assignment_due_in_15_days_custom_email,
            "email_subject": "Reminder: Assignments Due in 15 Days",
            "chat_content": (
                "Some of your assignments will due in 15 days.\n{{#each step.events}}\n"
                "Assignment title: {{assignment.title}}]nDue date: {{assignment.due_date}}\n"
                "Click here: {{assignment.link}}\n\n{{/each}}"
            ),
            "inapp_content": (
                "Some of your assignments will due in 15 days.<br />"
                "{{#each step.events}}Assignment title: {{assignment.title}}"
                "Due date: {{assignment.due_date}}<br/>{{/each}}"
            ),
            "config": config,
            "novu_api_key": novu_api_key,
        },
        {
            "event_name": "jeeves-assignment-due-in-7-days",
            "custom_email": await get_assignment_due_in_7_days_custom_email,
            "email_subject": "Reminder: Assignments Due in 7 Days",
            "chat_content": (
                "Some of your assignments will due in 7 days.\n{{#each step.events}}\n"
                "Assignment title: {{assignment.title}}]nDue date: {{assignment.due_date}}\n"
                "Click here: {{assignment.link}}\n\n{{/each}}"
            ),
            "inapp_content": (
                "Some of your assignments will due in 7 days.<br />{{#each step.events}}"
                "Assignment title: {{assignment.title}}</br>Due date: {{assignment.due_date}}<br />{{/each}}"
            ),
            "config": config,
            "novu_api_key": novu_api_key,
        },
        {
            "event_name": "jeeves-assignment-due-in-1-day",
            "custom_email": await get_assignment_due_in_1_day_custom_email,
            "email_subject": "Reminder: Assignments Due in One Day",
            "chat_content": (
                "Some of your assignments will due in one day.\n{{#each step.events}}\nAssignment title: "
                "{{assignment.title}}\nDue date: {{assignment.due_date}}\nClick here: {{assignment.link}}\n\n{{/each}}"
            ),
            "inapp_content": (
                "Some of your assignments will due in one day.<br />{{#each step.events}}"
                "Assignment title: {{assignment.title}}<br />Due date: {{assignment.due_date}}<br />{{/each}}"
            ),
            "config": config,
            "novu_api_key": novu_api_key,
        },
        {
            "event_name": "jeeves-assignment-overdue",
            "custom_email": await get_assignment_overdue_custom_email,
            "email_subject": "Urgent: Overdue Assignments - Action Required.",
            "chat_content": (
                "Some of your assignments are overdue.\n{{#each step.events}}\nAssignment title : "
                "{{assignment.title}}.\nDue date: {{assignment.due_date}}\nClick here: {{assignment.link}}\n\n{{/each}}"
            ),
            "inapp_content": (
                "Some of your assignments are overdue.<br />{{#each step.events}}"
                "Assignment title : {{assignment.title}}.<br />Due on: {{assignment.due_date}}<br />{{/each}}"
            ),
            "config": config,
            "novu_api_key": novu_api_key,
        },
        {
            "event_name": "jeeves-asset-expiring-in-7-days",
            "custom_email": await get_asset_expiring_in_7_days_custom_email,
            "email_subject": "Action Required: Asset Expiring In 7 Days",
            "chat_content": (
                "Some of your assets are about to expire in 7 days.\n{{#each step.events}}\n"
                'Asset title:  "{{asset.asset_title}}".\nClick here to update: {{asset.asset_link}}\n\n{{/each}}'
            ),
            "inapp_content": (
                "Some of your assets are about to expire in 7 days.<br />"
                '{{#each step.events}}Asset title: "{{asset.asset_title}}"<br />{{/each}}'
            ),
            "config": config,
            "novu_api_key": novu_api_key,
        },
        {
            "event_name": "jeeves-asset-expiring-in-30-days",
            "custom_email": await get_asset_expiring_in_30_days_custom_email,
            "email_subject": "Action Required: Asset Expiring In 30 Days",
            "chat_content": (
                "Some of your assets are about to expire in 30 days.\n{{#each step.events}}\n"
                'Asset title:  "{{asset.asset_title}}".\nClick here to update: {{asset.asset_link}}\n\n{{/each}}'
            ),
            "inapp_content": (
                "Some of your assets are about to expire in 30 days.<br />"
                '{{#each step.events}}Asset title: "{{asset.asset_title}}"<br />{{/each}}'
            ),
            "config": config,
            "novu_api_key": novu_api_key,
        },
        {
            "event_name": "jeeves-asset-expiring-in-1-day",
            "custom_email": await get_asset_expiring_in_1_day_custom_email,
            "email_subject": "Action Required: Asset Expiring In One Day",
            "chat_content": (
                "Some of your assets are about to expire in one day.\n{{#each step.events}}\n"
                'Asset title:  "{{asset.asset_title}}".\nClick here to update: {{asset.asset_link}}\n\n{{/each}}'
            ),
            "inapp_content": (
                "Some of your assets are about to expire in one day.<br />"
                '{{#each step.events}}Asset title: "{{asset.asset_title}}"<br />{{/each}}'
            ),
            "config": config,
            "novu_api_key": novu_api_key,
        },
        {
            "event_name": "jeeves-asset-expired",
            "custom_email": await get_asset_expired_custom_email,
            "email_subject": "Urgent: Expired Asset Requires Immediate Update",
            "chat_content": (
                "Some of your assets have expired. Update now to continue learning.\n{{#each step.events}}\n"
                'Asset title :  "{{asset.asset_title}}" .\nClick here to update: {{asset.asset_link}}\n\n{{/each}}'
            ),
            "inapp_content": (
                "Some of your assets have expired. Update now to continue learning.<br />"
                '{{#each step.events}}Asset Title: "{{asset.asset_title}}". <br />{{/each}}'
            ),
            "config": config,
            "novu_api_key": novu_api_key,
        },
        {
            "event_name": "jeeves-asset-deleted",
            "custom_email": await get_asset_deleted_custom_email,
            "email_subject": "Assets deleted from Jeeves",
            "chat_content": (
                "Following Assets are deleted from Jeeeves.\n"
                "{{#each step.events}}\nAsset title:  {{asset.asset_title}}\n\n{{/each}}"
            ),
            "inapp_content": (
                "Following Assets are deleted from Jeeeves<br />"
                "{{#each step.events}}Asset title:  {{asset.asset_title}}<br />{{/each}}"
            ),
            "config": config,
            "novu_api_key": novu_api_key,
        },
        {
            "event_name": "jeeves-asset-updated",
            "custom_email": await get_asset_updated_custom_email,
            "email_subject": "Assets updated in Jeeves",
            "chat_content": (
                "Following assets are updated in Jeeves.\n"
                "{{#each step.events}}\nAsset title:  {{asset.asset_title}}\n\n{{/each}}"
            ),
            "inapp_content": (
                "Following assets are updated in Jeeves.<br />"
                "{{#each step.events}}Asset title: {{asset.asset_title}}<br />{{/each}}"
            ),
            "config": config,
            "novu_api_key": novu_api_key,
        },
        {
            "event_name": "jeeves-asset-published",
            "custom_email": await get_asset_published_custom_email,
            "email_subject": "Assets published in Jeeves",
            "chat_content": (
                "Following assets are published in Jeeves.\n"
                "{{#each step.events}}\nAsset title:  {{asset.asset_title}}\n\n{{/each}}"
            ),
            "inapp_content": (
                "Following assets are published in Jeeves.<br />"
                "{{#each step.events}}Asset title: {{asset.asset_title}}<br />{{/each}}"
            ),
            "config": config,
            "novu_api_key": novu_api_key,
        },
        {
            "event_name": "jeeves-assignment-assigned",
            "custom_email": await get_assignment_assigned_custom_email,
            "email_subject": "New Assignment: {{todo_title}} Assigned by {{todo_assigned_by}}",
            "chat_content": "You have received a new assignment.\n{{todo_title}} :  {{todo_link}}",
            "inapp_content": "A new Assignment has been assigned to you.",
            "config": config,
            "novu_api_key": novu_api_key,
            "digest": False,
            "in_app_redirect_url": "/my-assignments/{{todo_id}}",
        },
        {
            "event_name": "jeeves-account-created",
            "custom_email": await get_account_created_custom_email,
            "email_subject": "Welcome to Jeeves {{ first_name }} {{{{ last_name }}}}",
            "chat_content": "New Jeeves account has been created successfully.",
            "inapp_content": "Welcome to JEEVES",
            "config": config,
            "novu_api_key": novu_api_key,
            "digest": False,
        },
        {
            "event_name": "jeeves-feedback-created",
            "custom_email": await get_feedback_created_custom_email,
            "email_subject": "New Feedback/Question on an asset",
            "chat_content": (
                "There's a new feedback/question on asset {{asset.asset_title}}.\n"
                "Remarks: {{feedback.feedback_text}}\nLink to edit the asset: {{asset.asset_link}}"
            ),
            "inapp_content": (
                "There's a new feedback/question on asset {{asset.asset_title}}."
                "<br />Remarks: {{feedback.feedback_text}}"
            ),
            "config": config,
            "novu_api_key": novu_api_key,
            "digest": False,
        },
        {
            "event_name": "jeeves-review-comment-added",
            "custom_email": await get_review_comment_added_custom_email,
            "email_subject": "New Review Comment on an asset",
            "chat_content": (
                "A new review comment has been posted on an asset {{asset.asset_title}}.\n"
                "Remarks: {{review.review_note}}\n"
                "Link to edit the asset: {{asset.asset_link}}"
            ),
            "inapp_content": (
                "A new review comment has been posted on "
                "an asset {{asset.asset_title}}.<br />Remarks: {{review.review_note}}"
            ),
            "config": config,
            "novu_api_key": novu_api_key,
        },
    ]
    await asyncio.gather(
        *[
            create_novu_workflow_template(**{**template, "custom_email": template["custom_email"]()})
            for template in template_definitions
            if template["event_name"] not in template_names
        ]
    )


def list_integration_provider(config: AppSettings, novu_api_key: str) -> list:
    """
    :return:
    """
    novu_client = IntegrationApi(url=config.jeeves.novu_url, api_key=novu_api_key)
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
    novu_client: IntegrationApi = IntegrationApi(url=config.jeeves.novu_url, api_key=novu_api_key)
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
                "from": config.jeeves.novu_sendgrid_sender_email,
                "senderName": config.jeeves.novu_sendgrid_sender_name,
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

    def __init__(self: "NovuSetup", jeeves: JeevesSpec) -> None:
        self.jeeves: JeevesSpec = jeeves
        self.config: AppSettings = get_settings()

    async def get_access_token(self: "NovuSetup") -> str:
        """
        Get the access token for the Novu environment
        """
        url = f"{self.config.jeeves.novu_url}/v1/auth/login"

        payload = {"email": self.config.jeeves.novu_admin_user, "password": self.config.jeeves.novu_admin_password}

        response = httpx.post(url=url, json=payload, timeout=120)

        if response.status_code >= 300:
            raise httpx.HTTPStatusError(
                f"Failed to get access token for Novu environment. Status code: {response.status_code}",
                request=response.request,
                response=response,
            )

        return response.json()["data"]["token"]

    async def get_organizations_by_name(self: "NovuSetup", organization_name: str, token: str) -> list:
        """
        List the organizations in the Novu environment
        """
        url = f"{self.config.jeeves.novu_url}/v1/organizations"

        response = httpx.get(url=url, headers={"Authorization": f"Bearer {token}"}, timeout=120)
        logger.debug(f"organisation name key: {response.json()}")
        if response.status_code >= 300:
            raise httpx.HTTPStatusError(
                f"Failed to get organization by name: {organization_name}", request=response.request, response=response
            )

        return [row for row in response.json()["data"] if row["name"] == organization_name]

    async def create_organization(self: "NovuSetup", token: str, org_name: str) -> dict:
        """
        Create an organization in the Novu environment
        """
        url = f"{self.config.jeeves.novu_url}/v1/organizations"

        payload = {
            "name": org_name,
        }

        response = httpx.post(url=url, headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=120)

        if response.status_code >= 300:
            raise httpx.HTTPStatusError(
                f"Failed to create organization: {org_name}", request=response.request, response=response
            )

        return response.json()

    def switch_organization(self: "NovuSetup", organization_id: str, token: str) -> str:
        """
        Switch the organization
        """
        url = f"{self.config.jeeves.novu_url}/v1/auth/organizations/{organization_id}/switch"

        response = httpx.post(url=url, headers={"Authorization": f"Bearer {token}"}, timeout=120)

        if response.status_code >= 300:
            raise httpx.HTTPStatusError(
                f"Failed to switch organization: {organization_id}", request=response.request, response=response
            )

        return response.json()["data"]

    async def get_environment_api_key(self: "NovuSetup", token: str) -> str:
        """
        Get novu env id
        """
        url = f"{self.config.jeeves.novu_url}/v1/environments"

        response = httpx.get(
            url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}, timeout=120
        )
        if response.status_code >= 300:
            raise httpx.HTTPStatusError(
                "Failed to get novu env id",
                request=response.request,
                response=response,
            )

        api_keys: list = [
            env.get("apiKeys")[0].get("key") for env in response.json()["data"] if env.get("name") == "Development"
        ]
        if api_keys and api_keys[0]:
            return api_keys[0]
        else:
            raise httpx.HTTPStatusError(
                "Failed to get novu env api key",
                request=response.request,
                response=response,
            )

    async def setup_novu(self: "NovuSetup") -> None:
        """
        Setup the Novu environment
        """
        config: AppSettings = get_settings()

        organization_name = f"jeeves_{self.jeeves.tenant}"
        access_token = await self.get_access_token()
        organization = await self.get_organizations_by_name(organization_name=organization_name, token=access_token)
        if not organization:
            organization = await self.create_organization(token=access_token, org_name=organization_name)
            organization_id = organization["data"]["id"]
        else:
            organization = organization[0]
            organization_id = organization["_id"]

        organization_token = self.switch_organization(organization_id=organization_id, token=access_token)

        api_keys = await self.get_environment_api_key(token=organization_token)

        # store in 1Password
        OnePasswordUtil(
            tenant=f"Jeeves_{self.jeeves.tenant}",
            server_item="application-config",
            vault="Jeeves",
        ).insert_if_not_exists(key="novu_api_key", value=api_keys)

        # create the templates
        await add_novu_templates(config=config, novu_api_key=api_keys)

        # add the integration provider
        add_integration_provider(config=config, novu_api_key=api_keys)

        log_info(f"Novu environment setup completed for tenant: {self.jeeves.tenant}")


class JeevesNovuSetupActivity(Activity):
    """
    JeevesNovuSetupActivity
    """

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=120)

    @staticmethod
    @activity.defn(name="JeevesNovuSetupActivity")
    async def defn(jeeves: JeevesSpec) -> None:
        """
        Callable for the activity
        """
        jeeves_novu_setup = NovuSetup(jeeves=jeeves)
        await jeeves_novu_setup.setup_novu()
