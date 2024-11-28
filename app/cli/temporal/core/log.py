from loguru import logger
from temporalio import activity, workflow


def log_info(message: str) -> None:
    """
    Log INFO level message
    :param message:
    :return:
    """
    try:
        if activity.in_activity():
            activity_info = activity.info()
            logger.info(
                f"workflow_id={activity_info.workflow_id} activity_name:{activity_info.activity_type} {message}"
            )
        else:
            workflow_info = workflow.info()
        logger.info(f"workflow_id={workflow_info.workflow_id} workflow_name:{workflow_info.workflow_type} {message}")
    except Exception:
        logger.info(message)


def log_error(message: str) -> None:
    """
    Log ERROR level message
    :param message:
    :return:
    """
    try:
        if activity.in_activity():
            activity_info = activity.info()
            logger.error(
                f"workflow_id={activity_info.workflow_id} activity_name:{activity_info.activity_type} {message}"
            )
        else:
            workflow_info = workflow.info()
            logger.error(
                f"workflow_id={workflow_info.workflow_id} workflow_name:{workflow_info.workflow_type} {message}"
            )
    except Exception:
        logger.error(message)
