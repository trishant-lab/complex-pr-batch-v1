import os

from app.utils.file_operations import get_opendal_file_client


async def get_template_from_file(template_path: str) -> str:
    """
    Load an HTML template from a file
    """
    base_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "templates")
    opendal_file_operations = get_opendal_file_client()
    template = await opendal_file_operations.read_file(os.path.join(base_path, template_path))
    return template.decode()


async def get_layout_content() -> str:
    """
    Get the layout content for the Novu notifications
    """
    return await get_template_from_file("novu/layout_content.html")


async def get_assignment_created_custom_email() -> str:
    """
    Get the custom email for the Novu notifications
    """
    return await get_template_from_file("novu/assignment_created_custom_email_content.html")


async def get_assignment_updated_custom_email() -> str:
    """
    Get the custom email for the Novu notifications
    """
    return await get_template_from_file("novu/assignment_updated_mail.html")


async def get_asset_created_custom_email() -> str:
    """
    Get the custom email for the Novu notifications
    """
    return await get_template_from_file("novu/asset_created_custom_mail.html")


async def get_assignment_due_in_15_days_custom_email() -> str:
    """
    Get the custom email for the Novu notifications
    """
    return await get_template_from_file("novu/assignment_due_in_15_days.html")


async def get_assignment_due_in_7_days_custom_email() -> str:
    """
    Get the custom email for the Novu notifications
    """
    return await get_template_from_file("novu/assignment_due_in_7_days.html")


async def get_assignment_due_in_1_day_custom_email() -> str:
    """
    Get the custom email for the Novu notifications
    """
    return await get_template_from_file("novu/assignment_due_in_1_day.html")


async def get_assignment_overdue_custom_email() -> str:
    """
    Get the custom email for the Novu notifications
    """
    return await get_template_from_file("novu/assignment_overdue_mail.html")


async def get_asset_expiring_in_7_days_custom_email() -> str:
    """
    Get the custom email for the Novu notifications
    """
    return await get_template_from_file("novu/asset_expiring_in_7_days.html")


async def get_asset_expiring_in_30_days_custom_email() -> str:
    """
    Get the custom email for the Novu notifications
    """
    return await get_template_from_file("novu/asset_expiring_in_30_days.html")


async def get_asset_expiring_in_1_day_custom_email() -> str:
    """
    Get the custom email for the Novu notifications
    """
    return await get_template_from_file("novu/asset_expiring_in_1_day.html")


async def get_asset_expired_custom_email() -> str:
    """
    Get the custom email for the Novu notifications
    """
    return await get_template_from_file("novu/asset_expired_mail.html")


async def get_asset_deleted_custom_email() -> str:
    """
    Get the custom email for the Novu notifications
    """
    return await get_template_from_file("novu/asset_deleted_mail.html")


async def get_asset_updated_custom_email() -> str:
    """
    Get the custom email for the Novu notifications
    """
    return await get_template_from_file("novu/asset_updated_mail.html")


async def get_asset_published_custom_email() -> str:
    """
    Get the custom email for the Novu notifications
    """
    return await get_template_from_file("novu/asset_published_mail.html")


async def get_assignment_assigned_custom_email() -> str:
    """
    Get the custom email for the Novu notifications
    """
    return await get_template_from_file("novu/assignment_assigned_mail.html")


async def get_account_created_custom_email() -> str:
    """
    Get the custom email for the Novu notifications
    """
    return await get_template_from_file("novu/account_created_mail.html")


async def get_feedback_created_custom_email() -> str:
    """
    Get the custom email for the Novu notifications
    """
    return await get_template_from_file("novu/feedback_created_mail.html")


async def get_review_comment_added_custom_email() -> str:
    """
    Get the custom email for the Novu notifications
    """
    return await get_template_from_file("novu/review_comment_added_mail.html")
