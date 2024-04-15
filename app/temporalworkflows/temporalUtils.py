from temporalio.client import Client

from app.core.settings import AppSettings, get_settings


async def check_workflow_status(workflow_id: str):
    """

    :param workflow_id:
    :type workflow_id:
    :return:
    :rtype:
    """
    config: AppSettings = get_settings()
    client = await Client.connect(config.temporal_dsn, namespace=config.temporal_namespace)

    handle = client.get_workflow_handle(
        workflow_id=workflow_id,
    )

    response = await handle.describe()
    return response.status.name
