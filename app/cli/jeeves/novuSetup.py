import requests
from loguru import logger
from novu.api import NotificationGroupApi, LayoutApi, IntegrationApi
from novu.dto import IntegrationDto

from app.cli.jeeves import TemplatePath
from app.cli.jeeves.common import JeevesSpec
from app.core.settings import AppSettings, get_settings
from app.onepasswordutil import OnePasswordUtil


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


def get_default_notification_layout_id(config: AppSettings, novu_api_key: str) -> str | None:
    """

    :return:
    """
    layout_name: str = "Default Layout"
    layout_client = LayoutApi(url=config.jeeves.novu_url, api_key=novu_api_key)
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
) -> dict:
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

    try:
        res = novu_client.create(
            integration=integration,
        )
        return res.to_camel_case()
    except Exception as e:
        logger.error(f"Failed to integrate provider: {e}")
        return {}


def create_novu_workflow_template(
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
    response = requests.post(url, headers=headers, json=data, timeout=10)
    if response.status_code >= 400:
        logger.error(f"Failed to create novu workflow template : {response.json()}")
    return response.status_code


def add_novu_templates(config: AppSettings, novu_api_key: str) -> None:
    """

    :param config:
    :param novu_api_key:
    :return:
    """
    # jeeves-assignment-created
    assignment_created_custom_email: str = '<p class="editor-paragraph" dir="ltr"><span>Hi {{eventsubscriber.first_name}} {{eventsubscriber.last_name}}</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>The following assignments created in Jeeves.</span></p><p class="editor-paragraph" dir="ltr"><span>{{#each step.events}}</span></p><p class="editor-paragraph" dir="ltr"><span>Assignment Title: </span><a href="{{assignment.link}}" class="editor-link"><span>{{assignment.name}}</span></a></p><p class="editor-paragraph" dir="ltr"><span>Due date: {{assignment.duedate}}</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>{{/each}}</span></p><p class="editor-paragraph" dir="ltr"><span>Regards,</span></p><p class="editor-paragraph" dir="ltr"><span>Team Jeeves</span></p>'  # noqa
    assignment_created_subject: str = "Assignments are created in Jeeves"
    assignment_created_chat_content: str = "Assignments are created in Jeeves.\n{{#each step.events}}\nAssignment title : {{assignment.name}}.\nClick here: {{assignment.link}}\n\n{{/each}}"  # noqa
    assignment_created_inapp_content: str = "Assignments are created in Jeeves.\n<br />\n{{#each step.events}}\nAssignment title : {{assignment.name}}.\nDue on: {{assignment.duedate}}\n<br />\n{{/each}}"  # noqa

    create_novu_workflow_template(
        event_name="jeeves-assignment-created",
        custom_email=assignment_created_custom_email,
        email_subject=assignment_created_subject,
        chat_content=assignment_created_chat_content,
        inapp_content=assignment_created_inapp_content,
        config=config,
        novu_api_key=novu_api_key
    )

    # jeeves-assignment-updated
    assignment_updated_custom_email: str = '<p class="editor-paragraph" dir="ltr"><span>Hi {{eventsubscriber.first_name}} {{eventsubscriber.last_name}}</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>The following assignments updated in Jeeves.</span></p><p class="editor-paragraph" dir="ltr"><span>{{#each step.events}}</span></p><p class="editor-paragraph" dir="ltr"><span>Assignment Title: </span><a href="{{assignment.link}}" class="editor-link"><span>{{assignment.name}}</span></a></p><p class="editor-paragraph" dir="ltr"><span>Due date: {{assignment.duedate}}</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>{{/each}}</span></p><p class="editor-paragraph" dir="ltr"><span>Regards,</span></p><p class="editor-paragraph" dir="ltr"><span>Team Jeeves</span></p>'  # noqa
    assignment_updated_subject: str = "Assignments are updated in Jeeves"
    assignment_updated_chat_content: str = "Assignments are updated in Jeeves.\n{{#each step.events}}\nAssignment title : {{assignment.name}}.\nClick here: {{assignment.link}}\n\n{{/each}}"  # noqa
    assignment_updated_inapp_content: str = "Assignments are updated in Jeeves.\n<br />\n{{#each step.events}}\nAssignment title : {{assignment.name}}.\nDue on: {{assignment.duedate}}\n<br />\n{{/each}}"

    create_novu_workflow_template(
        event_name="jeeves-assignment-updated",
        custom_email=assignment_updated_custom_email,
        email_subject=assignment_updated_subject,
        chat_content=assignment_updated_chat_content,
        inapp_content=assignment_updated_inapp_content,
        config=config,
        novu_api_key=novu_api_key
    )

    # jeeves-asset-created
    asset_created_custom_email: str = '<p class="editor-paragraph" dir="ltr"><span>Hi {{eventsubscriber.first_name}},</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>Following assets are created in Jeeves:</span></p><p class="editor-paragraph" dir="ltr"><br></p><p class="editor-paragraph" dir="ltr"><span>{{#each step.events}}</span></p><p class="editor-paragraph" dir="ltr"><span>Asset Title: {{asset.asset_title}}</span></p><p class="editor-paragraph" dir="ltr"><span>Application: {{asset.application}}</span></p><p class="editor-paragraph" dir="ltr"><span>Category: {{asset.category}}</span></p><p class="editor-paragraph" dir="ltr"><span>Author: {{asset.author}}</span></p><p class="editor-paragraph" dir="ltr"><span>Click to View: {{asset.asset_link}}</span></p><p class="editor-paragraph" dir="ltr"><br></p><p class="editor-paragraph" dir="ltr"><span>{{/each}}</span></p><p class="editor-paragraph" dir="ltr"><span>Regards,</span></p><p class="editor-paragraph" dir="ltr"><span>Team Jeeves</span></p>'
    asset_created_subject: str = "New Assets created in Jeeves"
    asset_created_chat_content: str = "New assets are created.\n\n{{#each step.events}}\nAsset title:  {{asset.asset_title}} \nClick to View: {{asset.asset_link}}\n\n{{/each}}"
    aasset_created_inapp_content: str = "New assets are created.\n<br />\n{{#each step.events}}\nAsset title:  {{asset.asset_title}} \n<br />\n{{/each}}"

    create_novu_workflow_template(
        event_name="jeeves-asset-created",
        custom_email=asset_created_custom_email,
        email_subject=asset_created_subject,
        chat_content=asset_created_chat_content,
        inapp_content=aasset_created_inapp_content,
        config=config,
        novu_api_key=novu_api_key
    )

    # jeeves-assignment-due-in-15-days
    assignment_due_15_custom_email: str = '<p class="editor-paragraph" dir="ltr"><span>Hi {{eventsubscriber.first_name}} {{eventsubscriber.last_name}},</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>This is a reminder that several assignments will due in 15 days. Kindly take note of the following details:</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>{{#each step.events}}</span></p><p class="editor-paragraph" dir="ltr"><span>Assignment Title: </span><a href="{{assignment.link}}" class="editor-link"><span>{{assignment.title}}</span></a></p><p class="editor-paragraph" dir="ltr"><span>Due Date: {{assignment.due_date}}</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>{{/each}}</span></p><p class="editor-paragraph" dir="ltr"><span>We kindly request that you ensure timely completion of these assignments to meet the deadline.</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>Regards,</span></p><p class="editor-paragraph" dir="ltr"><span>Team Jeeves</span></p>'
    assignment_due_15_subject: str = "Reminder: Assignments Due in 15 Days"
    assignment_due_15_chat_content: str = "Some of your assignments will due in 15 days.\n{{#each step.events}}\nAssignment title: {{assignment.title}}]nDue date: {{assignment.due_date}}\nClick here: {{assignment.link}}\n\n{{/each}}"
    assignment_due_15_inapp_content: str = "Some of your assignments will due in 15 days.<br />{{#each step.events}}Assignment title: {{assignment.title}}Due date: {{assignment.due_date}}<br />{{/each}}"

    create_novu_workflow_template(
        event_name="jeeves-assignment-due-in-15-days",
        custom_email=assignment_due_15_custom_email,
        email_subject=assignment_due_15_subject,
        chat_content=assignment_due_15_chat_content,
        inapp_content=assignment_due_15_inapp_content,
        config=config,
        novu_api_key=novu_api_key
    )

    # jeeves-assignment-due-in-7-days
    assignment_due_7_custom_email: str = '<p class="editor-paragraph" dir="ltr"><span>Hi {{eventsubscriber.first_name}} {{eventsubscriber.last_name}},</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>This is a reminder that several assignments will due in 7 days. Kindly take note of the following details:</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>{{#each step.events}}</span></p><p class="editor-paragraph" dir="ltr"><span>Assignment Title: </span><a href="{{assignment.link}}" class="editor-link"><span>{{assignment.title}}</span></a></p><p class="editor-paragraph" dir="ltr"><span>Due Date: {{assignment.due_date}}</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>{{/each}}</span></p><p class="editor-paragraph" dir="ltr"><span>We kindly request that you ensure timely completion of these assignments to meet the deadline.</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>Regards,</span></p><p class="editor-paragraph" dir="ltr"><span>Team Jeeves</span></p>'
    assignment_due_7_subject: str = "Reminder: Assignments Due in 7 Days"
    assignment_due_7_chat_content: str = "Some of your assignments will due in 7 days.\n{{#each step.events}}\nAssignment title: {{assignment.title}}]nDue date: {{assignment.due_date}}\nClick here: {{assignment.link}}\n\n{{/each}}"
    assignment_due_7_inapp_content: str = "Some of your assignments will due in 7 days.<br />{{#each step.events}}Assignment title: {{assignment.title}}</br>Due date: {{assignment.due_date}}<br />{{/each}}"

    create_novu_workflow_template(
        event_name="jeeves-assignment-due-in-7-days",
        custom_email=assignment_due_7_custom_email,
        email_subject=assignment_due_7_subject,
        chat_content=assignment_due_7_chat_content,
        inapp_content=assignment_due_7_inapp_content,
        config=config,
        novu_api_key=novu_api_key
    )

    # jeeves-assignment-due-in-1-day
    assignment_due_1_custom_email: str = '<p class="editor-paragraph" dir="ltr"><span>Hi {{eventsubscriber.first_name}} {{eventsubscriber.last_name}},</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>This is a reminder that several assignments will due in one day. Kindly take note of the following details:</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>{{#each step.events}}</span></p><p class="editor-paragraph" dir="ltr"><span>Assignment Title: </span><a href="{{assignment.link}}" class="editor-link"><span>{{assignment.title}}</span></a></p><p class="editor-paragraph" dir="ltr"><span>Due Date: {{assignment.due_date}}</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>{{/each}}</span></p><p class="editor-paragraph" dir="ltr"><span>We kindly request that you ensure timely completion of these assignments to meet the deadline.</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>Regards,</span></p><p class="editor-paragraph" dir="ltr"><span>Team Jeeves</span></p>'
    assignment_due_1_subject: str = "Reminder: Assignments Due in One Day"
    assignment_due_1_inapp_content: str = "Some of your assignments will due in one day.<br />{{#each step.events}}Assignment title: {{assignment.title}}<br />Due date: {{assignment.due_date}}<br />{{/each}}"
    assignment_due_1_chat_content: str = "Some of your assignments will due in one day.\n{{#each step.events}}\nAssignment title: {{assignment.title}}\nDue date: {{assignment.due_date}}\nClick here: {{assignment.link}}\n\n{{/each}}"

    create_novu_workflow_template(
        event_name="jeeves-assignment-due-in-1-day",
        custom_email=assignment_due_1_custom_email,
        email_subject=assignment_due_1_subject,
        chat_content=assignment_due_1_chat_content,
        inapp_content=assignment_due_1_inapp_content,
        config=config,
        novu_api_key=novu_api_key
    )

    # jeeves-assignment-overdue
    assignment_over_due_custom_email: str = '<p class="editor-paragraph" dir="ltr"><span>Hi {{eventsubscriber.first_name}} {{eventsubscriber.last_name}}</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>The following assignment(s) are overdue.</span></p><p class="editor-paragraph" dir="ltr"><span>{{#each step.events}}</span></p><p class="editor-paragraph" dir="ltr"><span>Assignment Title: </span><a href="{{assignment.link}}" class="editor-link"><span>{{assignment.title}}</span></a></p><p class="editor-paragraph" dir="ltr"><span>Due date: {{assignment.due_date}}</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>{{/each}}</span></p><p class="editor-paragraph" dir="ltr"><span>We kindly request that you ensure timely completion of these assignments to meet the deadline.</span></p><p class="editor-paragraph" dir="ltr"><span>Regards,</span></p><p class="editor-paragraph" dir="ltr"><span>Team Jeeves</span></p>'
    assignment_over_due_subject: str = "Urgent: Overdue Assignments - Action Required."
    assignment_over_due_inapp_content: str = "Some of your assignments are overdue.<br />{{#each step.events}}Assignment title : {{assignment.title}}.<br />Due on: {{assignment.due_date}}<br />{{/each}}"
    assignment_over_due_chat_content: str = "Some of your assignments are overdue.\n{{#each step.events}}\nAssignment title : {{assignment.title}}.\nDue date: {{assignment.due_date}}\nClick here: {{assignment.link}}\n\n{{/each}}"
    create_novu_workflow_template(
        event_name="jeeves-assignment-overdue",
        custom_email=assignment_over_due_custom_email,
        email_subject=assignment_over_due_subject,
        chat_content=assignment_over_due_chat_content,
        inapp_content=assignment_over_due_inapp_content,
        config=config,
        novu_api_key=novu_api_key
    )

    # jeeves-asset-expiring-in-7-days
    asset_expiring_7_custom_email: str = '<p class="editor-paragraph" dir="ltr"><span>Hi {{eventsubscriber.first_name}} {{eventsubscriber.last_name}},</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>This is to inform you that several of your assets will expire in 7 days. Please take action and update the asset details.</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>{{#each step.events}}</span></p><p class="editor-paragraph" dir="ltr"><span>Asset Title: {{asset.asset_title}}</span></p><p class="editor-paragraph" dir="ltr"><span>Expiration Date: {{asset.expiration_date}}</span></p><p class="editor-paragraph" dir="ltr"><span>You can update the asset information by clicking [</span><a href="{{asset.asset_link}}" class="editor-link"><span>here</span></a><span>].</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>{{/each}}</span></p><p class="editor-paragraph" dir="ltr"><span>Please take immediate action to update the information for these assets to ensure smooth operations.</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>Regards,</span></p><p class="editor-paragraph" dir="ltr"><span>Team Jeeves</span></p>'
    asset_expiring_7_subject: str = "Action Required: Asset Expiring In 7 Days"
    asset_expiring_7_inapp_content: str = 'Some of your assets are about to expire in 7 days.<br />{{#each step.events}}Asset title: "{{asset.asset_title}}"<br />{{/each}}'
    asset_expiring_7_chat_content: str = 'Some of your assets are about to expire in 7 days.\n{{#each step.events}}\nAsset title:  "{{asset.asset_title}}".\nClick here to update: {{asset.asset_link}}\n\n{{/each}}'
    create_novu_workflow_template(
        event_name="jeeves-asset-expiring-in-7-days",
        custom_email=asset_expiring_7_custom_email,
        email_subject=asset_expiring_7_subject,
        chat_content=asset_expiring_7_chat_content,
        inapp_content=asset_expiring_7_inapp_content,
        config=config,
        novu_api_key=novu_api_key
    )

    # jeeves-asset-expiring-in-7-days
    asset_expiring_30_custom_email: str = '<p class="editor-paragraph" dir="ltr"><span>Hi {{eventsubscriber.first_name}} {{eventsubscriber.last_name}},</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>This is to inform you that several of your assets will expire in 30 days. Please take action and update the asset details.</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>{{#each step.events}}</span></p><p class="editor-paragraph" dir="ltr"><span>Asset Title: {{asset.asset_title}}</span></p><p class="editor-paragraph" dir="ltr"><span>Expiration Date: {{asset.expiration_date}}</span></p><p class="editor-paragraph" dir="ltr"><span>You can update the asset information by clicking [</span><a href="{{asset.asset_link}}" class="editor-link"><span>here</span></a><span>].</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>{{/each}}</span></p><p class="editor-paragraph" dir="ltr"><span>Please take immediate action to update the information for these assets to ensure smooth operations.</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>Regards,</span></p><p class="editor-paragraph" dir="ltr"><span>Team Jeeves</span></p>'
    asset_expiring_30_subject: str = "Action Required: Asset Expiring In 30 Days"
    asset_expiring_30_inapp_content: str = 'Some of your assets are about to expire in 30 days.<br />{{#each step.events}}Asset title: "{{asset.asset_title}}"<br />{{/each}}'
    asset_expiring_30_chat_content: str = 'Some of your assets are about to expire in 30 days.\n{{#each step.events}}\nAsset title:  "{{asset.asset_title}}".\nClick here to update: {{asset.asset_link}}\n\n{{/each}}'
    create_novu_workflow_template(
        event_name="jeeves-asset-expiring-in-7-days",
        custom_email=asset_expiring_30_custom_email,
        email_subject=asset_expiring_30_subject,
        chat_content=asset_expiring_30_chat_content,
        inapp_content=asset_expiring_30_inapp_content,
        config=config,
        novu_api_key=novu_api_key
    )

    # jeeves-asset-expiring-in-7-days
    asset_expiring_1_custom_email: str = '<p class="editor-paragraph" dir="ltr"><span>Hi {{eventsubscriber.first_name}} {{eventsubscriber.last_name}},</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>This is to inform you that several of your assets will expire in one day. Please take action and update the asset details.</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>{{#each step.events}}</span></p><p class="editor-paragraph" dir="ltr"><span>Asset Title: {{asset.asset_title}}</span></p><p class="editor-paragraph" dir="ltr"><span>Expiration Date: {{asset.expiration_date}}</span></p><p class="editor-paragraph" dir="ltr"><span>You can update the asset information by clicking [</span><a href="{{asset.asset_link}}" class="editor-link"><span>here</span></a><span>].</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>{{/each}}</span></p><p class="editor-paragraph" dir="ltr"><span>Please take immediate action to update the information for these assets to ensure smooth operations.</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>Regards,</span></p><p class="editor-paragraph" dir="ltr"><span>Team Jeeves</span></p>'
    asset_expiring_1_subject: str = "Action Required: Asset Expiring In One Day"
    asset_expiring_1_inapp_content: str = 'Some of your assets are about to expire in one day.<br />{{#each step.events}}Asset title: "{{asset.asset_title}}"<br />{{/each}}'
    asset_expiring_1_chat_content: str = 'Some of your assets are about to expire in one day.\n{{#each step.events}}\nAsset title:  "{{asset.asset_title}}".\nClick here to update: {{asset.asset_link}}\n\n{{/each}}'
    create_novu_workflow_template(
        event_name="jeeves-asset-expiring-in-7-days",
        custom_email=asset_expiring_1_custom_email,
        email_subject=asset_expiring_1_subject,
        chat_content=asset_expiring_1_chat_content,
        inapp_content=asset_expiring_1_inapp_content,
        config=config,
        novu_api_key=novu_api_key
    )

    # jeeves-asset-expired
    asset_expired_custom_email: str = '<p class="editor-paragraph" dir="ltr"><span>Hi {{eventsubscriber.first_name}} {{eventsubscriber.last_name}},</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>We regret to inform you that several of your assets have expired and require immediate attention. Please take note of the following details:</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>{{#each step.events}}</span></p><p class="editor-paragraph" dir="ltr"><span>Asset Title: {{asset.asset_title}}</span></p><p class="editor-paragraph" dir="ltr"><span>Expiration Date: {{asset.expiration_date}}</span></p><p class="editor-paragraph" dir="ltr"><span>You can update the asset information by clicking [</span><a href="{{asset.asset_link}}" class="editor-link"><span>here</span></a><span>].</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>{{/each}}</span></p><p class="editor-paragraph" dir="ltr"><span>Please take immediate action to update the information for these assets to ensure smooth operations.</span></p><p class="editor-paragraph" dir="ltr"><span>Regards,</span></p><p class="editor-paragraph" dir="ltr"><span>Team Jeeves</span></p>'
    asset_expired_subject: str = "Urgent: Expired Asset Requires Immediate Update"
    asset_expired_inapp_content: str = 'Some of your assets have expired. Update now to continue learning.<br />{{#each step.events}}Asset Title: "{{asset.asset_title}}". <br />{{/each}}'
    asset_expired_chat_content: str = 'Some of your assets have expired. Update now to continue learning.\n{{#each step.events}}\nAsset title :  "{{asset.asset_title}}" .\nClick here to update: {{asset.asset_link}}\n\n{{/each}}'

    create_novu_workflow_template(
        event_name="jeeves-asset-expired",
        custom_email=asset_expired_custom_email,
        email_subject=asset_expired_subject,
        chat_content=asset_expired_chat_content,
        inapp_content=asset_expired_inapp_content,
        config=config,
        novu_api_key=novu_api_key
    )

    # jeeves-asset-deleted
    asset_deleted_custom_email: str = '<p class="editor-paragraph" dir="ltr"><span>Hi {{eventsubscriber.first_name}} {{eventsubscriber.last_name}},</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>Following assets are deleted from Jeeves.</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>{{#each step.events}}</span></p><p class="editor-paragraph" dir="ltr"><span>Asset Title: {{asset.asset_title}}</span></p><p class="editor-paragraph" dir="ltr"><span>Application: {{asset.application}}</span></p><p class="editor-paragraph" dir="ltr"><span>Category: {{asset.category}}</span></p><p class="editor-paragraph" dir="ltr"><span>Author: {{asset.author}}</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>{{/each}}</span></p><p class="editor-paragraph" dir="ltr"><span>Regards,</span></p><p class="editor-paragraph" dir="ltr"><span>Team Jeeves</span></p>'
    asset_deleted_subject: str = "Assets deleted from Jeeves"
    asset_deleted_inapp_content: str = "Following Assets are deleted from Jeeeves<br />{{#each step.events}}Asset title:  {{asset.asset_title}}<br />{{/each}}"
    asset_deleted_chat_content: str = "Following Assets are deleted from Jeeeves.\n{{#each step.events}}\nAsset title:  {{asset.asset_title}}\n\n{{/each}}"

    create_novu_workflow_template(
        event_name="jeeves-asset-deleted",
        custom_email=asset_deleted_custom_email,
        email_subject=asset_deleted_subject,
        chat_content=asset_deleted_chat_content,
        inapp_content=asset_deleted_inapp_content,
        config=config,
        novu_api_key=novu_api_key
    )

    # jeeves-asset-updated
    asset_updated_custom_email: str = '<p class="editor-paragraph" dir="ltr"><span>Hi {{eventsubscriber.first_name}},</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>Following assets in Jeeves have been updated to provide you with an even better learning experience:</span></p><p class="editor-paragraph" dir="ltr"><br></p><p class="editor-paragraph" dir="ltr"><span>{{#each step.events}}</span></p><p class="editor-paragraph" dir="ltr"><span>Asset Title: {{asset.asset_title}}</span></p><p class="editor-paragraph" dir="ltr"><span>Application: {{asset.application}}</span></p><p class="editor-paragraph" dir="ltr"><span>Category: {{asset.category}}</span></p><p class="editor-paragraph" dir="ltr"><span>Author: {{asset.author}}</span></p><p class="editor-paragraph" dir="ltr"><span>Click to View: {{asset.asset_link}}</span></p><p class="editor-paragraph" dir="ltr"><br></p><p class="editor-paragraph" dir="ltr"><span>{{/each}}</span></p><p class="editor-paragraph" dir="ltr"><span>Regards,</span></p><p class="editor-paragraph" dir="ltr"><span>Team Jeeves</span></p>'
    asset_updated_subject: str = "Assets updated in Jeeves"
    asset_updated_inapp_content: str = "Following assets are updated in Jeeves.<br />{{#each step.events}}Asset title: {{asset.asset_title}}<br />{{/each}}"
    asset_updated_chat_content: str = "Following assets are updated in Jeeves.\n{{#each step.events}}\nAsset title:  {{asset.asset_title}}\n\n{{/each}}"

    create_novu_workflow_template(
        event_name="jeeves-asset-updated",
        custom_email=asset_updated_custom_email,
        email_subject=asset_updated_subject,
        chat_content=asset_updated_chat_content,
        inapp_content=asset_updated_inapp_content,
        config=config,
        novu_api_key=novu_api_key
    )

    # jeeves-asset-published
    asset_published_custom_email: str = '<p class="editor-paragraph" dir="ltr"><span>Hi {{eventsubscriber.first_name}},</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>Following assets are published in Jeeves to provide you with an even better learning experience:</span></p><p class="editor-paragraph" dir="ltr"><br></p><p class="editor-paragraph" dir="ltr"><span>{{#each step.events}}</span></p><p class="editor-paragraph" dir="ltr"><span>Asset Title: {{asset.asset_title}}</span></p><p class="editor-paragraph" dir="ltr"><span>Application: {{asset.application}}</span></p><p class="editor-paragraph" dir="ltr"><span>Category: {{asset.category}}</span></p><p class="editor-paragraph" dir="ltr"><span>Author: {{asset.author}}</span></p><p class="editor-paragraph" dir="ltr"><span>Click to View: {{asset.asset_link}}</span></p><p class="editor-paragraph" dir="ltr"><br></p><p class="editor-paragraph" dir="ltr"><span>{{/each}}</span></p><p class="editor-paragraph" dir="ltr"><span>Regards,</span></p><p class="editor-paragraph" dir="ltr"><span>Team Jeeves</span></p>'
    asset_published_subject: str = "Assets published in Jeeves"
    asset_published_inapp_content: str = "Following assets are published in Jeeves.<br />{{#each step.events}}Asset title: {{asset.asset_title}}<br />{{/each}}"
    asset_published_chat_content: str = "Following assets are published in Jeeves.\n{{#each step.events}}\nAsset title:  {{asset.asset_title}}\n\n{{/each}}"

    create_novu_workflow_template(
        event_name="jeeves-asset-published",
        custom_email=asset_published_custom_email,
        email_subject=asset_published_subject,
        chat_content=asset_published_chat_content,
        inapp_content=asset_published_inapp_content,
        config=config,
        novu_api_key=novu_api_key
    )

    # jeeves-assignment-assigned
    assignment_assigned_custom_email: str = '<p class="editor-paragraph" dir="ltr"><span>Hi {{ first_name }},</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>You have received a new assignment.</span></p><p class="editor-paragraph" dir="ltr"><span>Assignment Title: {{todo_title}}</span></p><p class="editor-paragraph" dir="ltr"><span>Assigned By: {{todo_assigned_by}}</span></p><p class="editor-paragraph" dir="ltr"><span>Click to View: {{todo_link}}</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>Regards,</span></p><p class="editor-paragraph" dir="ltr"><span>{{email_signature}}</span></p>'
    assignment_assigned_subject: str = "New Assignment: {{todo_title}} Assigned by {{todo_assigned_by}}"
    assignment_assigned_inapp_content: str = "A new Assignment has been assigned to you."
    assignment_assigned_chat_content: str = "You have received a new assignment.\n{{todo_title}} :  {{todo_link}}"

    create_novu_workflow_template(
        event_name="jeeves-assignment-assigned",
        custom_email=assignment_assigned_custom_email,
        email_subject=assignment_assigned_subject,
        chat_content=assignment_assigned_chat_content,
        inapp_content=assignment_assigned_inapp_content,
        config=config,
        digest=False,
        in_app_redirect_url="/sprint/my-assignments/{{todo_id}}"
        if config.env == "integration"
        else "/my-assignments/{{todo_id}}",
        novu_api_key=novu_api_key
    )

    # jeeves-account-created
    account_created_custom_email: str = '<p class="editor-paragraph" dir="ltr"><span>Hi {{first_name}}</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>Your JEEVES account has been created successfully.</span></p><p class="editor-paragraph" dir="ltr"><span>Click here to get started: {{jeeves_link}}</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>Regards,</span></p><p class="editor-paragraph" dir="ltr"><span>{{email_signature}}</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph"><br></p><p class="editor-paragraph"><br></p><p class="editor-paragraph"><br></p><p class="editor-paragraph"><br></p><p class="editor-paragraph"><br></p><p class="editor-paragraph"><br></p><p class="editor-paragraph"><br></p><p class="editor-paragraph"><br></p><p class="editor-paragraph"><br></p><p class="editor-paragraph"><br></p><p class="editor-paragraph"><br></p><p class="editor-paragraph"><br></p>'
    account_created_subject: str = "Welcome to Jeeves {{ first_name }} {{{{ last_name }}}}"
    account_created_inapp_content: str = "Welcome to JEEVES"
    account_created_chat_content: str = "New Jeeves account has been created successfully."

    create_novu_workflow_template(
        event_name="jeeves-account-created",
        custom_email=account_created_custom_email,
        email_subject=account_created_subject,
        chat_content=account_created_chat_content,
        inapp_content=account_created_inapp_content,
        config=config,
        digest=False,
        novu_api_key=novu_api_key
    )

    # jeeves-feedback-created
    feedback_created_custom_email: str = '<p class="editor-paragraph" dir="ltr"><span>There\'s a new feedback/question on an asset.</span></p><p class="editor-paragraph" dir="ltr"><br><span>Asset Title: {{asset.asset_title}}</span></p><p class="editor-paragraph" dir="ltr"><span>Application: {{asset.application}}</span></p><p class="editor-paragraph" dir="ltr"><span>Category: {{asset.category}}</span></p><p class="editor-paragraph" dir="ltr"><span>Author: {{asset.author_name}}({{asset.author}})</span></p><p class="editor-paragraph" dir="ltr"><span>Sender: {{feedback.sender_user_name}}({{feedback.sender_user_email}})</span></p><p class="editor-paragraph" dir="ltr"><span>Remarks: {{feedback.feedback_text}}</span></p><p class="editor-paragraph"><br></p><p class="editor-paragraph" dir="ltr"><span>Link to edit the asset: {{asset.asset_link}}</span></p><p class="editor-paragraph"><span>--</span></p><p class="editor-paragraph" dir="ltr"><span>Team Jeeves</span></p>'
    feedback_created_subject: str = "New Feedback/Question on an asset"
    feedback_created_inapp_content: str = (
        "There's a new feedback/question on asset {{asset.asset_title}}.<br />Remarks: {{feedback.feedback_text}}"
    )
    feedback_created_chat_content: str = "There's a new feedback/question on asset {{asset.asset_title}}.\nRemarks: {{feedback.feedback_text}}\nLink to edit the asset: {{asset.asset_link}}"

    create_novu_workflow_template(
        event_name="jeeves-feedback-created",
        custom_email=feedback_created_custom_email,
        email_subject=feedback_created_subject,
        chat_content=feedback_created_chat_content,
        inapp_content=feedback_created_inapp_content,
        config=config,
        digest=False,
        novu_api_key=novu_api_key
    )


def add_integration_provider(config: AppSettings, novu_api_key: str) -> None:
    """

    :return:
    """
    # adding email provider sendgrid
    integrate_provider(
        provider="sendgrid",
        channel="email",
        credentials={
            "apiKey": config.sendgrid_api_key,
            "from": "developer@314ecorp.com",
            "senderName": "Jeeves",
        },
        active=True,
        config=config,
        novu_api_key=novu_api_key
    )
    # adding in app provider novu
    integrate_provider(
        provider="novu",
        channel="in_app",
        credentials={},
        active=True,
        config=config,
        novu_api_key=novu_api_key
    )


class NovuSetup:
    """
    This class will be used to setup the Novu environment
    """
    def __init__(self, jeeves: JeevesSpec) -> None:
        self.jeeves: JeevesSpec = jeeves
        self.config: AppSettings = get_settings()

    def get_access_token(self):
        """
        Get the access token for the Novu environment
        """
        url = f"{self.config.jeeves.novu_url}/v1/auth/login"

        payload = {
            "email": self.config.jeeves.novu_admin_user,
            "password": self.config.jeeves.novu_admin_password
        }

        response = requests.post(
            url=url,
            json=payload
        )

        if response.status_code >= 300:
            raise Exception(f"Failed to get access token for Novu environment")

        return response.json()['data']['token']

    def get_organizations_by_name(self, organization_name: str, token: str):
        """
        List the organizations in the Novu environment
        """
        url = f"{self.config.jeeves.novu_url}/v1/organizations"

        response = requests.get(
            url=url,
            headers={
                "Authorization": f"Bearer {token}"
            }
        )

        if response.status_code >= 300:
            raise Exception(f"Failed to get organization by name: {organization_name}")

        return [row for row in response.json()['data'] if row['name'] == organization_name]

    def create_organization(self, token: str, org_name: str):
        """

        """
        url = f"{self.config.jeeves.novu_url}/v1/organizations"

        payload = {
            "name": org_name,
        }

        response = requests.post(
            url=url,
            headers={
                "Authorization": f"Bearer {token}"
            },
            json=payload
        )

        if response.status_code >= 300:
            raise Exception(f"Failed to create organization: {org_name}")

        return response.json()

    def get_organization_api_key(self, token: str):
        """
        Get the API keys for the organization
        """
        url = f"{self.config.jeeves.novu_url}/v1/environments/api-keys"

        response = requests.get(
            url=url,
            headers={
                "Authorization": f"Bearer {token}"
            }
        )

        if response.status_code >= 300:
            raise Exception(f"Failed to get API keys for organization status_code:{response.status_code}")

        return response.json()['data'][0]['key']

    def switch_organization(self, organization_id: str, token: str):
        """
        Switch the organization
        """
        url = f"{self.config.jeeves.novu_url}/v1/auth/organizations/{organization_id}/switch"

        response = requests.post(
            url=url,
            headers={
                "Authorization": f"Bearer {token}"
            },
        )

        if response.status_code >= 300:
            raise Exception(f"Failed to switch organization: {organization_id}")

        return response.json()['data']

    def setup_novu(self):
        """
        Setup the Novu environment
        """
        config: AppSettings = get_settings()

        organization_name = f"jeeves_{self.jeeves.tenant}"
        access_token = self.get_access_token()
        organization = self.get_organizations_by_name(organization_name=organization_name, token=access_token)
        if not organization:
            organization = self.create_organization(token=access_token, org_name=organization_name)
            organization_id = organization['data']['id']
        else:
            organization = organization[0]
            organization_id = organization['_id']

        organization_token = self.switch_organization(organization_id=organization_id, token=access_token)
        api_keys = self.get_organization_api_key(token=organization_token)

        # store in 1Password
        OnePasswordUtil(
            tenant=f"Jeeves_{self.jeeves.tenant}",
            server_item="application-config",
            vault="Jeeves",
        ).insert_if_not_exists(key="novu_api_key", value=api_keys)

        # create the templates
        add_novu_templates(config=config, novu_api_key=api_keys)

        # add the integration provider
        add_integration_provider(config=config, novu_api_key=api_keys)
