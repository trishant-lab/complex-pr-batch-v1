import os

from app.utils.file_operations import get_opendal_file_client


async def get_template_from_file(template_path: str) -> str:
    """
    Load an HTML template from a file
    """
    base_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "templates")
    opendal_file_operations = get_opendal_file_client()
    return await opendal_file_operations.read_file_str(os.path.join(base_path, template_path))


async def get_jeeves_broadcast_layout_content() -> str:
    """
    Get the layout content for the Jeeves broadcast v2 workflow email step
    """
    return await get_template_from_file("novu/jeeves_broadcast_layout.html")
