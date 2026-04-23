import asyncio
from datetime import timedelta

import aiohttp
import httpx
from loguru import logger
from novu.api import IntegrationApi, NotificationTemplateApi
from novu.dto import IntegrationDto
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_info
from app.cli.temporal.jeeves.jeeves import JeevesSpec
from app.cli.temporal.jeeves.models.jeeves_spec import SpaceSpec
from app.cli.temporal.jeeves.template_main import (
    get_account_created_custom_email,
    get_asset_annotation_preset_share_email,
    get_asset_feedback_received_email,
    get_asset_shared_email,
    get_assignment_assigned_custom_email,
    get_assignment_completion_email,
    get_assignment_due_in_1_day_custom_email,
    get_assignment_due_in_7_days_custom_email,
    get_assignment_due_in_15_days_custom_email,
    get_assignment_overdue_custom_email,
    get_assignment_revoked_email,
    get_bulk_import_complete_email,
    get_daily_digest_email,
    get_digest_layout_content,
    get_layout_content,
    get_review_comment_added_custom_email,
    get_asset_assigned_email,
    get_weekly_digest_email,
)
from app.core.settings import AppSettings, get_settings
from app.one_password_util import OnePasswordUtil

DIGEST_LAYOUT_NAME = "Jeeves Digest Layout"
JEEVES_LAYOUT_NAME = "Jeeves Layout"


def get_default_notification_group_id(novu_url: str, novu_api_key: str) -> str | None:
    """Fetch the default notification group ID from Novu."""
    response = httpx.get(
        f"{novu_url}/v1/notification-groups",
        headers={"Authorization": f"ApiKey {novu_api_key}"},
        timeout=10,
    )
    response.raise_for_status()
    for group in response.json().get("data", []):
        return group.get("_id")
    return None


def get_default_notification_layout_id(
    novu_url: str, novu_api_key: str, layout_name: str = JEEVES_LAYOUT_NAME
) -> str | None:
    """Fetch a layout's ID by name from Novu (case-sensitive match)."""
    response = httpx.get(
        f"{novu_url}/v1/layouts",
        headers={"Authorization": f"ApiKey {novu_api_key}"},
        params={"page": 0, "pageSize": 100},
        timeout=10,
    )
    response.raise_for_status()
    for layout in response.json().get("data", []):
        if layout.get("name") == layout_name:
            return layout.get("_id")
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


def build_step(step_name: str, step_type: str, content: str, subject: str = "", content_type: str = "editor") -> dict:
    """
    build a step for a novu workflow template
    :param step_name:
    :param step_type:
    :param content:
    :param subject:
    :param content_type:
    :return:
    """
    return {
        "name": step_name,
        "active": True,
        "shouldStopOnFail": False,
        "template": {
            "content": content,
            "subject": subject,
            "type": step_type,
            "contentType": content_type,
        },
    }


async def create_novu_workflow_template(
    event_name: str,
    custom_email: str,
    email_subject: str,
    config: AppSettings,
    novu_api_key: str,
    digest_amount: int = 5,
    chat_content: str | None = None,
    inapp_content: str | None = None,
    digest: bool = True,
    layout_name: str = JEEVES_LAYOUT_NAME,
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
    layout_id = get_default_notification_layout_id(config.jeeves.novu_url, novu_api_key, layout_name=layout_name)
    notification_group = get_default_notification_group_id(config.jeeves.novu_url, novu_api_key)
    steps: list = []
    if digest:
        digest_step = build_step("Digest", "digest", "")
        digest_step["metadata"] = {
            "type": "regular",
            "amount": digest_amount,
            "unit": "minutes",
            "backoff": False,
        }
        steps.append(digest_step)

    email_step = build_step("Email", "email", custom_email, email_subject, "customHtml")
    email_step["template"]["layoutId"] = layout_id
    email_step["replyCallback"] = {"active": False}
    steps.append(email_step)

    if inapp_content:
        ia_step = build_step("In-App", "in_app", inapp_content)
        if in_app_redirect_url:
            ia_step["template"]["cta"] = {"type": "redirect", "data": {"url": in_app_redirect_url}, "action": {}}
        steps.append(ia_step)

    if chat_content:
        steps.append(build_step("Chat", "chat", chat_content))

    data = {
        "name": event_name,
        "notificationGroupId": notification_group,
        "active": True,
        "steps": steps,
    }

    headers = {
        "Authorization": f"ApiKey {novu_api_key}",
        "Content-Type": "application/json",
    }

    url = f"{config.jeeves.novu_url}/v1/workflows"
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
    jeeves_layout: str | None = get_default_notification_layout_id(
        novu_url=config.jeeves.novu_url, novu_api_key=novu_api_key
    )
    jeeves_digest_layout: str | None = get_default_notification_layout_id(
        novu_url=config.jeeves.novu_url, novu_api_key=novu_api_key, layout_name=DIGEST_LAYOUT_NAME
    )
    if jeeves_layout is None:
        layout_content = await get_layout_content()
        await create_novu_notification_layout(
            config=config,
            novu_api_key=novu_api_key,
            layout_name=JEEVES_LAYOUT_NAME,
            layout_content=layout_content,
        )
    if jeeves_digest_layout is None:
        layout_content = await get_digest_layout_content()
        await create_novu_notification_layout(
            config=config,
            novu_api_key=novu_api_key,
            layout_name=DIGEST_LAYOUT_NAME,
            layout_content=layout_content,
        )

    template_definitions: list[dict] = [
        {
            "event_name": "jeeves-assignment-due-in-15-days",
            "custom_email": await get_assignment_due_in_15_days_custom_email(),
            "email_subject": "Reminder: Assignments Due in 15 Days",
            "chat_content": ('Assignment "{{assignment.title}}" will due in 15 days'),
            "inapp_content": (
                "Some of your assignments will due in 15 days.<br />{{#each step.events}}"
                "Assignment title: {{assignment.title}}Due date: {{assignment.due_date}}<br />{{/each}}"
            ),
            "config": config,
            "novu_api_key": novu_api_key,
        },
        {
            "event_name": "jeeves-assignment-due-in-7-days",
            "custom_email": await get_assignment_due_in_7_days_custom_email(),
            "email_subject": "Reminder: Assignments Due in 7 Days",
            "chat_content": ('Assignment "{{assignment.title}}" will due in 7 days'),
            "inapp_content": (
                "Some of your assignments will due in 7 days.<br />{{#each step.events}}"
                "Assignment title: {{assignment.title}}<br />Due date: {{assignment.due_date}}<br />{{/each}}"
            ),
            "config": config,
            "novu_api_key": novu_api_key,
        },
        {
            "event_name": "jeeves-assignment-due-in-1-day",
            "custom_email": await get_assignment_due_in_1_day_custom_email(),
            "email_subject": "Reminder: Assignments Due in One Day",
            "chat_content": ('Assignment "{{assignment.title}}" will due in 1 day'),
            "inapp_content": (
                "Some of your assignments will due in one day.<br />{{#each step.events}}"
                "Assignment title: {{assignment.title}}<br />Due date: {{assignment.due_date}}<br />{{/each}}"
            ),
            "config": config,
            "novu_api_key": novu_api_key,
        },
        {
            "event_name": "jeeves-assignment-overdue",
            "custom_email": await get_assignment_overdue_custom_email(),
            "email_subject": "Urgent: Overdue Assignments - Action Required.",
            "chat_content": ('Assignment "{{assignment.title}}" is over due'),
            "inapp_content": (
                "Some of your assignments are overdue.<br />{{#each step.events}}"
                "Assignment title : {{assignment.title}}.<br />Due on: {{assignment.due_date}}<br />{{/each}}"
            ),
            "config": config,
            "novu_api_key": novu_api_key,
        },
        {
            "event_name": "jeeves-assignment-assigned",
            "custom_email": await get_assignment_assigned_custom_email(),
            "email_subject": "New Assignment: {{assignment_title}}",
            "inapp_content": "You have been assigned a new assignment: "
            "{{assignment_title}} by {{assignment_assigned_by}}.",
            "config": config,
            "novu_api_key": novu_api_key,
            "digest": False,
            "in_app_redirect_url": "{{redirecturl}}{{assignment_link}}",
        },
        {
            "event_name": "jeeves-account-created",
            "custom_email": await get_account_created_custom_email(),
            "email_subject": "Welcome to Jeeves {{ first_name }} {{{{ last_name }}}}",
            "chat_content": "New Jeeves account has been created successfully.",
            "inapp_content": "Welcome to JEEVES",
            "config": config,
            "novu_api_key": novu_api_key,
            "digest": False,
        },
        {
            "event_name": "jeeves-review-comment-added",
            "custom_email": await get_review_comment_added_custom_email(),
            "email_subject": "You've Been Mentioned in a Comment on {{asset.asset_title}}",
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
        {
            "event_name": "jeeves-asset-assigned",
            "custom_email": await get_asset_assigned_email(),
            "email_subject": "New Asset Assigned: {{asset.asset_title}}(Authoring Stage: {{asset.asset_stage_name}})",
            "chat_content": ("A new Asset {{asset.asset_title}} has been assigned to you."),
            "inapp_content": ("A new Asset {{asset.asset_title}} has been assigned to you."),
            "in_app_redirect_url": "/assets/{{asset.asset_id}}/preview?version={{asset.version}}",
            "config": config,
            "novu_api_key": novu_api_key,
        },
        {
            "event_name": "jeeves-assignment-completion",
            "custom_email": await get_assignment_completion_email(),
            "email_subject": "Assignment Completed: '{{{assignment.name}}}'",
            "chat_content": (
                "Congratulations! 🎉 You have successfully "
                "completed the assignment '{{assignment.name}}' on {{assignment.completed_date}}."
            ),
            "inapp_content": (
                "Congratulations! 🎉 You have successfully completed the "
                "assignment '{{assignment.name}}' on {{assignment.completed_date}}."
            ),
            "in_app_redirect_url": "{{assignment.link}}",
            "config": config,
            "novu_api_key": novu_api_key,
        },
        {
            "event_name": "jeeves-assignment-revoked",
            "custom_email": await get_assignment_revoked_email(),
            "email_subject": "Assignment has been updated with new assets.",
            "chat_content": (
                "Your completion status has been reset for {{assignment_title}}."
                " Please review the updated assets to mark it complete again."
            ),
            "inapp_content": (
                "Your completion status has been reset for {{assignment_title}}."
                " Please review the updated assets to mark it complete again."
            ),
            "in_app_redirect_url": "/my-assignments/{{assignment_id}}",
            "config": config,
            "novu_api_key": novu_api_key,
        },
        {
            "event_name": "jeeves-asset-shared",
            "custom_email": await get_asset_shared_email(),
            "email_subject": "Learning Content(s) Shared With You",
            "chat_content": ("Learning content(s) has been shared with you."),
            "inapp_content": ("Learning content(s) has been shared with you."),
            "in_app_redirect_url": "/resources/shared",
            "config": config,
            "novu_api_key": novu_api_key,
        },
        {
            "event_name": "jeeves-asset-annotation-preset-share",
            "custom_email": await get_asset_annotation_preset_share_email(),
            "email_subject": "{{shared_by_name}} shared an annotation preset with you",
            "inapp_content": (
                "{{shared_by_name}} has shared the annotation preset {{preset_name}} with you."
                " You can now use this preset in the Video Editor."
            ),
            "config": config,
            "novu_api_key": novu_api_key,
        },
        {
            "event_name": "jeeves-weekly-digest",
            "custom_email": await get_weekly_digest_email(),
            "email_subject": "{{#if show_space_in_subject}}Jeeves Weekly for {{{space_display_name}}} "
            "space ({{{digest_date_range}}}) — Updates, Progress & Actions{{else}}Jeeves Weekly "
            "({{{digest_date_range}}}) — Updates, Progress & Actions{{/if}}",
            "config": config,
            "novu_api_key": novu_api_key,
            "digest": False,
            "layout_name": DIGEST_LAYOUT_NAME,
        },
        {
            "event_name": "jeeves-daily-digest",
            "custom_email": await get_daily_digest_email(),
            "email_subject": "{{#if show_space_in_subject}}Jeeves Daily for {{{space_display_name}}}"
            "space — Updates, Progress & Actions{{else}}Jeeves Daily — Updates, Progress & Actions{{/if}}",
            "config": config,
            "novu_api_key": novu_api_key,
            "digest": False,
            "layout_name": DIGEST_LAYOUT_NAME,
        },
        {
            "event_name": "jeeves-bulk-import-complete",
            "custom_email": await get_bulk_import_complete_email(),
            "email_subject": "Your bulk upload has been processed",
            "inapp_content": (
                "Your assets uploaded through bulk publish have been processed."
                " You can view and manage them all in one place."
            ),
            "config": config,
            "novu_api_key": novu_api_key,
            "digest": False,
            "in_app_redirect_url": "/assets/bulk-publish/{{instance_id}}",
        },
        {
            "event_name": "jeeves-asset-feedback-received",
            "custom_email": await get_asset_feedback_received_email(),
            "email_subject": "New feedback on {{asset.asset_name}}",
            "inapp_content": (
                "New feedback has been received on {{asset.asset_name}} from {{learner_name}} at {{timestamp}}. "
                "Feedback: {{feedback}}"
            ),
            "config": config,
            "novu_api_key": novu_api_key,
            "digest": False,
            "in_app_redirect_url": "/assets/{{asset.asset_id}}/preview?version={{asset.asset_version}}&tab=activity",
        },
    ]
    await asyncio.gather(
        *[
            create_novu_workflow_template(**template)
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

    def __init__(self: "NovuSetup", jeeves: JeevesSpec, space_name: str) -> None:
        self.jeeves: JeevesSpec = jeeves
        self.config: AppSettings = get_settings()
        self.space_name: str = space_name

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

        organization_name = f"{self.space_name}"
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
        await OnePasswordUtil(
            tenant=f"{self.space_name}",
            server_item="application-config",
            vault="Jeeves",
        ).insert_if_not_exists(key="novu_api_key", value=api_keys)

        # create the templates
        await add_novu_templates(config=config, novu_api_key=api_keys)

        # add the integration provider
        add_integration_provider(config=config, novu_api_key=api_keys)

        log_info(f"Novu environment setup completed for tenant: {self.space_name}")


class JeevesNovuSetupActivityModel(LaunchpadCLIBaseModel):
    """
    JeevesNovuSetupActivityModel
    """

    jeeves: JeevesSpec | SpaceSpec
    space_name: str


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
    async def defn(activity_model: JeevesNovuSetupActivityModel) -> None:
        """
        Callable for the activity
        """
        jeeves_novu_setup = NovuSetup(jeeves=activity_model.jeeves, space_name=activity_model.space_name)
        await jeeves_novu_setup.setup_novu()
