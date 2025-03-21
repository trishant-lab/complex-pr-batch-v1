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


def list_novu_notification_template(
    config: AppSettings,
    novu_api_key: str,
    page: int = 0,
    limit: int = 100,
) -> list | None:
    """
    :return:
    """
    novu_client = NotificationTemplateApi(url=config.jeeves.novu_url, api_key=novu_api_key)
    response = novu_client.list(page=page, limit=limit)
    template_names: list = [template.to_camel_case().get("name", "") for template in response.data if response]
    return template_names


async def add_novu_templates(config: AppSettings, novu_api_key: str) -> None:
    """

    :param config:
    :param novu_api_key:
    :return:
    """
    template_names: list = list_novu_notification_template(config=config, novu_api_key=novu_api_key)
    jeeves_layout: str | None = get_default_notification_layout_id(config=config, novu_api_key=novu_api_key)
    if jeeves_layout is None:
        layout_content = get_layout_content()
        await create_novu_notification_layout(
            config=config,
            novu_api_key=novu_api_key,
            layout_name="Jeeves Layout",
            layout_content=layout_content,
        )

    # jeeves-assignment-created
    if "jeeves-assignment-created" not in template_names:
        assignment_created_custom_email: str = get_assignment_created_custom_email()
        assignment_created_subject: str = "Assignments are created in Jeeves"
        assignment_created_chat_content: str = (
            "Assignments are created in Jeeves.\n{{#each step.events}}\n"
            "Assignment title : {{assignment.name}}.\nClick here: {{assignment.link}}\n\n{{/each}}"
        )
        assignment_created_inapp_content: str = (
            "Assignments are created in Jeeves.\n<br />\n{{#each step.events}}\n"
            "Assignment title : {{assignment.name}}.\nDue on: {{assignment.duedate}}\n<br />\n{{/each}}"
        )

        await create_novu_workflow_template(
            event_name="jeeves-assignment-created",
            custom_email=assignment_created_custom_email,
            email_subject=assignment_created_subject,
            chat_content=assignment_created_chat_content,
            inapp_content=assignment_created_inapp_content,
            config=config,
            novu_api_key=novu_api_key,
        )

    # jeeves-assignment-updated
    if "jeeves-assignment-updated" not in template_names:
        assignment_updated_custom_email: str = get_assignment_updated_custom_email()
        assignment_updated_subject: str = "Assignments are updated in Jeeves"
        assignment_updated_chat_content: str = (
            "Assignments are updated in Jeeves.\n{{#each step.events}}\n"
            "Assignment title : {{assignment.name}}.\nClick here: {{assignment.link}}\n\n{{/each}}"
        )
        assignment_updated_inapp_content: str = (
            "Assignments are updated in Jeeves.\n<br />\n{{#each step.events}}\n"
            "Assignment title : {{assignment.name}}.\nDue on: {{assignment.duedate}}\n<br />\n{{/each}}"
        )

        await create_novu_workflow_template(
            event_name="jeeves-assignment-updated",
            custom_email=assignment_updated_custom_email,
            email_subject=assignment_updated_subject,
            chat_content=assignment_updated_chat_content,
            inapp_content=assignment_updated_inapp_content,
            config=config,
            novu_api_key=novu_api_key,
        )

    # jeeves-asset-created
    if "jeeves-asset-created" not in template_names:
        asset_created_custom_email: str = get_asset_created_custom_email()
        asset_created_subject: str = "New Assets created in Jeeves"
        asset_created_chat_content: str = (
            "New assets are created.\n\n{{#each step.events}}\n"
            "Asset title:  {{asset.asset_title}} \nClick to View: {{asset.asset_link}}\n\n{{/each}}"
        )
        aasset_created_inapp_content: str = (
            "New assets are created.\n<br />\n{{#each step.events}}\n"
            "Asset title:  {{asset.asset_title}} \n<br />\n{{/each}}"
        )

        await create_novu_workflow_template(
            event_name="jeeves-asset-created",
            custom_email=asset_created_custom_email,
            email_subject=asset_created_subject,
            chat_content=asset_created_chat_content,
            inapp_content=aasset_created_inapp_content,
            config=config,
            novu_api_key=novu_api_key,
        )

    # jeeves-assignment-due-in-15-days
    if "jeeves-assignment-due-in-15-days" not in template_names:
        assignment_due_15_custom_email: str = get_assignment_due_in_15_days_custom_email()
        assignment_due_15_subject: str = "Reminder: Assignments Due in 15 Days"
        assignment_due_15_chat_content: str = (
            "Some of your assignments will due in 15 days.\n{{#each step.events}}\n"
            "Assignment title: {{assignment.title}}]nDue date: {{assignment.due_date}}\n"
            "Click here: {{assignment.link}}\n\n{{/each}}"
        )
        assignment_due_15_inapp_content: str = (
            "Some of your assignments will due in 15 days.<br />"
            "{{#each step.events}}Assignment title: {{assignment.title}}Due date: {{assignment.due_date}}<br/>{{/each}}"
        )

        await create_novu_workflow_template(
            event_name="jeeves-assignment-due-in-15-days",
            custom_email=assignment_due_15_custom_email,
            email_subject=assignment_due_15_subject,
            chat_content=assignment_due_15_chat_content,
            inapp_content=assignment_due_15_inapp_content,
            config=config,
            novu_api_key=novu_api_key,
        )

    # jeeves-assignment-due-in-7-days
    if "jeeves-assignment-due-in-7-days" not in template_names:
        assignment_due_7_custom_email: str = get_assignment_due_in_7_days_custom_email()
        assignment_due_7_subject: str = "Reminder: Assignments Due in 7 Days"
        assignment_due_7_chat_content: str = (
            "Some of your assignments will due in 7 days.\n{{#each step.events}}\n"
            "Assignment title: {{assignment.title}}]nDue date: {{assignment.due_date}}\n"
            "Click here: {{assignment.link}}\n\n{{/each}}"
        )
        assignment_due_7_inapp_content: str = (
            "Some of your assignments will due in 7 days.<br />{{#each step.events}}"
            "Assignment title: {{assignment.title}}</br>Due date: {{assignment.due_date}}<br />{{/each}}"
        )

        await create_novu_workflow_template(
            event_name="jeeves-assignment-due-in-7-days",
            custom_email=assignment_due_7_custom_email,
            email_subject=assignment_due_7_subject,
            chat_content=assignment_due_7_chat_content,
            inapp_content=assignment_due_7_inapp_content,
            config=config,
            novu_api_key=novu_api_key,
        )

    # jeeves-assignment-due-in-1-day
    if "jeeves-assignment-due-in-1-day" not in template_names:
        assignment_due_1_custom_email: str = get_assignment_due_in_1_day_custom_email()
        assignment_due_1_subject: str = "Reminder: Assignments Due in One Day"
        assignment_due_1_inapp_content: str = (
            "Some of your assignments will due in one day.<br />{{#each step.events}}"
            "Assignment title: {{assignment.title}}<br />Due date: {{assignment.due_date}}<br />{{/each}}"
        )
        assignment_due_1_chat_content: str = (
            "Some of your assignments will due in one day.\n{{#each step.events}}\nAssignment title: "
            "{{assignment.title}}\nDue date: {{assignment.due_date}}\nClick here: {{assignment.link}}\n\n{{/each}}"
        )

        await create_novu_workflow_template(
            event_name="jeeves-assignment-due-in-1-day",
            custom_email=assignment_due_1_custom_email,
            email_subject=assignment_due_1_subject,
            chat_content=assignment_due_1_chat_content,
            inapp_content=assignment_due_1_inapp_content,
            config=config,
            novu_api_key=novu_api_key,
        )

    # jeeves-assignment-overdue
    if "jeeves-assignment-overdue" not in template_names:
        assignment_over_due_custom_email: str = get_assignment_overdue_custom_email()
        assignment_over_due_subject: str = "Urgent: Overdue Assignments - Action Required."
        assignment_over_due_inapp_content: str = (
            "Some of your assignments are overdue.<br />{{#each step.events}}"
            "Assignment title : {{assignment.title}}.<br />Due on: {{assignment.due_date}}<br />{{/each}}"
        )
        assignment_over_due_chat_content: str = (
            "Some of your assignments are overdue.\n{{#each step.events}}\nAssignment title : "
            "{{assignment.title}}.\nDue date: {{assignment.due_date}}\nClick here: {{assignment.link}}\n\n{{/each}}"
        )
        await create_novu_workflow_template(
            event_name="jeeves-assignment-overdue",
            custom_email=assignment_over_due_custom_email,
            email_subject=assignment_over_due_subject,
            chat_content=assignment_over_due_chat_content,
            inapp_content=assignment_over_due_inapp_content,
            config=config,
            novu_api_key=novu_api_key,
        )

    # jeeves-asset-expiring-in-7-days
    if "jeeves-asset-expiring-in-7-days" not in template_names:
        asset_expiring_7_custom_email: str = get_asset_expiring_in_7_days_custom_email()
        asset_expiring_7_subject: str = "Action Required: Asset Expiring In 7 Days"
        asset_expiring_7_inapp_content: str = (
            "Some of your assets are about to expire in 7 days.<br />"
            '{{#each step.events}}Asset title: "{{asset.asset_title}}"<br />{{/each}}'
        )
        asset_expiring_7_chat_content: str = (
            "Some of your assets are about to expire in 7 days.\n{{#each step.events}}\n"
            'Asset title:  "{{asset.asset_title}}".\nClick here to update: {{asset.asset_link}}\n\n{{/each}}'
        )
        await create_novu_workflow_template(
            event_name="jeeves-asset-expiring-in-7-days",
            custom_email=asset_expiring_7_custom_email,
            email_subject=asset_expiring_7_subject,
            chat_content=asset_expiring_7_chat_content,
            inapp_content=asset_expiring_7_inapp_content,
            config=config,
            novu_api_key=novu_api_key,
        )

    # jeeves-asset-expiring-in-30-days
    if "jeeves-asset-expiring-in-30-days" not in template_names:
        asset_expiring_30_custom_email: str = get_asset_expiring_in_30_days_custom_email()
        asset_expiring_30_subject: str = "Action Required: Asset Expiring In 30 Days"
        asset_expiring_30_inapp_content: str = (
            "Some of your assets are about to expire in 30 days.<br />"
            '{{#each step.events}}Asset title: "{{asset.asset_title}}"<br />{{/each}}'
        )
        asset_expiring_30_chat_content: str = (
            "Some of your assets are about to expire in 30 days.\n{{#each step.events}}\n"
            'Asset title:  "{{asset.asset_title}}".\nClick here to update: {{asset.asset_link}}\n\n{{/each}}'
        )
        await create_novu_workflow_template(
            event_name="jeeves-asset-expiring-in-30-days",
            custom_email=asset_expiring_30_custom_email,
            email_subject=asset_expiring_30_subject,
            chat_content=asset_expiring_30_chat_content,
            inapp_content=asset_expiring_30_inapp_content,
            config=config,
            novu_api_key=novu_api_key,
        )

    # jeeves-asset-expiring-in-1-days
    if "jeeves-asset-expiring-in-1-day" not in template_names:
        asset_expiring_1_custom_email: str = get_asset_expiring_in_1_day_custom_email()
        asset_expiring_1_subject: str = "Action Required: Asset Expiring In One Day"
        asset_expiring_1_inapp_content: str = (
            "Some of your assets are about to expire in one day.<br />"
            '{{#each step.events}}Asset title: "{{asset.asset_title}}"<br />{{/each}}'
        )
        asset_expiring_1_chat_content: str = (
            "Some of your assets are about to expire in one day.\n{{#each step.events}}\n"
            'Asset title:  "{{asset.asset_title}}".\nClick here to update: {{asset.asset_link}}\n\n{{/each}}'
        )
        await create_novu_workflow_template(
            event_name="jeeves-asset-expiring-in-1-day",
            custom_email=asset_expiring_1_custom_email,
            email_subject=asset_expiring_1_subject,
            chat_content=asset_expiring_1_chat_content,
            inapp_content=asset_expiring_1_inapp_content,
            config=config,
            novu_api_key=novu_api_key,
        )

    # jeeves-asset-expired
    if "jeeves-asset-expired" not in template_names:
        asset_expired_custom_email: str = get_asset_expired_custom_email()
        asset_expired_subject: str = "Urgent: Expired Asset Requires Immediate Update"
        asset_expired_inapp_content: str = (
            "Some of your assets have expired. Update now to continue learning.<br />"
            '{{#each step.events}}Asset Title: "{{asset.asset_title}}". <br />{{/each}}'
        )
        asset_expired_chat_content: str = (
            "Some of your assets have expired. Update now to continue learning.\n{{#each step.events}}\n"
            'Asset title :  "{{asset.asset_title}}" .\nClick here to update: {{asset.asset_link}}\n\n{{/each}}'
        )

        await create_novu_workflow_template(
            event_name="jeeves-asset-expired",
            custom_email=asset_expired_custom_email,
            email_subject=asset_expired_subject,
            chat_content=asset_expired_chat_content,
            inapp_content=asset_expired_inapp_content,
            config=config,
            novu_api_key=novu_api_key,
        )

    # jeeves-asset-deleted
    if "jeeves-asset-deleted" not in template_names:
        asset_deleted_custom_email: str = get_asset_deleted_custom_email()
        asset_deleted_subject: str = "Assets deleted from Jeeves"
        asset_deleted_inapp_content: str = (
            "Following Assets are deleted from Jeeeves<br />"
            "{{#each step.events}}Asset title:  {{asset.asset_title}}<br />{{/each}}"
        )
        asset_deleted_chat_content: str = (
            "Following Assets are deleted from Jeeeves.\n"
            "{{#each step.events}}\nAsset title:  {{asset.asset_title}}\n\n{{/each}}"
        )

        await create_novu_workflow_template(
            event_name="jeeves-asset-deleted",
            custom_email=asset_deleted_custom_email,
            email_subject=asset_deleted_subject,
            chat_content=asset_deleted_chat_content,
            inapp_content=asset_deleted_inapp_content,
            config=config,
            novu_api_key=novu_api_key,
        )

    # jeeves-asset-updated
    if "jeeves-asset-updated" not in template_names:
        asset_updated_custom_email: str = get_asset_updated_custom_email()
        asset_updated_subject: str = "Assets updated in Jeeves"
        asset_updated_inapp_content: str = (
            "Following assets are updated in Jeeves.<br />"
            "{{#each step.events}}Asset title: {{asset.asset_title}}<br />{{/each}}"
        )
        asset_updated_chat_content: str = (
            "Following assets are updated in Jeeves.\n"
            "{{#each step.events}}\nAsset title:  {{asset.asset_title}}\n\n{{/each}}"
        )

        await create_novu_workflow_template(
            event_name="jeeves-asset-updated",
            custom_email=asset_updated_custom_email,
            email_subject=asset_updated_subject,
            chat_content=asset_updated_chat_content,
            inapp_content=asset_updated_inapp_content,
            config=config,
            novu_api_key=novu_api_key,
        )

    # jeeves-asset-published
    if "jeeves-asset-published" not in template_names:
        asset_published_custom_email: str = get_asset_published_custom_email()
        asset_published_subject: str = "Assets published in Jeeves"
        asset_published_inapp_content: str = (
            "Following assets are published in Jeeves.<br />"
            "{{#each step.events}}Asset title: {{asset.asset_title}}<br />{{/each}}"
        )
        asset_published_chat_content: str = (
            "Following assets are published in Jeeves.\n"
            "{{#each step.events}}\nAsset title:  {{asset.asset_title}}\n\n{{/each}}"
        )

        await create_novu_workflow_template(
            event_name="jeeves-asset-published",
            custom_email=asset_published_custom_email,
            email_subject=asset_published_subject,
            chat_content=asset_published_chat_content,
            inapp_content=asset_published_inapp_content,
            config=config,
            novu_api_key=novu_api_key,
        )

    # jeeves-assignment-assigned
    if "jeeves-assignment-assigned" not in template_names:
        assignment_assigned_custom_email: str = get_assignment_assigned_custom_email()
        assignment_assigned_subject: str = "New Assignment: {{todo_title}} Assigned by {{todo_assigned_by}}"
        assignment_assigned_inapp_content: str = "A new Assignment has been assigned to you."
        assignment_assigned_chat_content: str = "You have received a new assignment.\n{{todo_title}} :  {{todo_link}}"

        await create_novu_workflow_template(
            event_name="jeeves-assignment-assigned",
            custom_email=assignment_assigned_custom_email,
            email_subject=assignment_assigned_subject,
            chat_content=assignment_assigned_chat_content,
            inapp_content=assignment_assigned_inapp_content,
            config=config,
            digest=False,
            in_app_redirect_url=(
                "/sprint/my-assignments/{{todo_id}}" if config.env == "integration" else "/my-assignments/{{todo_id}}"
            ),
            novu_api_key=novu_api_key,
        )

    # jeeves-account-created
    if "jeeves-account-created" not in template_names:
        account_created_custom_email: str = get_account_created_custom_email()
        account_created_subject: str = "Welcome to Jeeves {{ first_name }} {{{{ last_name }}}}"
        account_created_inapp_content: str = "Welcome to JEEVES"
        account_created_chat_content: str = "New Jeeves account has been created successfully."

        await create_novu_workflow_template(
            event_name="jeeves-account-created",
            custom_email=account_created_custom_email,
            email_subject=account_created_subject,
            chat_content=account_created_chat_content,
            inapp_content=account_created_inapp_content,
            config=config,
            digest=False,
            novu_api_key=novu_api_key,
        )

    # jeeves-feedback-created
    if "jeeves-feedback-created" not in template_names:
        feedback_created_custom_email: str = get_feedback_created_custom_email()
        feedback_created_subject: str = "New Feedback/Question on an asset"
        feedback_created_inapp_content: str = (
            "There's a new feedback/question on asset {{asset.asset_title}}.<br />Remarks: {{feedback.feedback_text}}"
        )
        feedback_created_chat_content: str = (
            "There's a new feedback/question on asset {{asset.asset_title}}.\n"
            "Remarks: {{feedback.feedback_text}}\nLink to edit the asset: {{asset.asset_link}}"
        )

        await create_novu_workflow_template(
            event_name="jeeves-feedback-created",
            custom_email=feedback_created_custom_email,
            email_subject=feedback_created_subject,
            chat_content=feedback_created_chat_content,
            inapp_content=feedback_created_inapp_content,
            config=config,
            digest=False,
            novu_api_key=novu_api_key,
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

    # todo: we will keep this method until we upgrade production and
    # after making sure that the new method is working fine
    async def get_organization_api_key(self: "NovuSetup", token: str, organization_id: str) -> str:
        """
        Get the API keys for the organization
        """
        url = f"{self.config.jeeves.novu_url}/v1/environments/api-keys"

        response = httpx.get(
            url=url,
            headers={"Authorization": f"Bearer {token}", "novu-environment-id": f"{organization_id}"},
            timeout=120,
        )
        logger.debug(f"API key: {response.json()}")
        if response.status_code >= 300:
            raise httpx.HTTPStatusError(
                f"Failed to get API keys for organization status_code:{response.status_code}, {response.json()}",
                request=response.request,
                response=response,
            )

        return response.json()["data"][0]["key"]

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

    # todo: we will keep this method until we upgrade production and
    # after making sure that the new method is working fine
    async def get_environment_id(self: "NovuSetup", token: str) -> str:
        """
        Get novu env id
        """
        url = f"{self.config.jeeves.novu_url}/v1/environments"

        response = httpx.get(
            url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}, timeout=120
        )
        if response.status_code >= 300:
            raise httpx.HTTPStatusError("Failed to get novu env id", request=response.request, response=response)

        return response.json()["data"][0]["_id"]

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
