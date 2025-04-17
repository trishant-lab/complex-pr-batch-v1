import logging
import sys
from collections.abc import Callable
from typing import Any

from loguru import logger


def patch(logger_method: Callable) -> Callable:
    """
    function extends loguru internal function to bind kwargs to extra parameter
    kwargs   :   key word args passed at the time of logging , all parameters except message
    """

    def patched(self: Any, message: str, *args: Any, **kwargs: Any) -> None:
        self = self.opt(depth=1).bind(**kwargs)
        logger_method(self, message, *args, **kwargs)

    return patched


for log_method in ("trace", "debug", "info", "error", "warning", "critical"):
    method = getattr(logger.__class__, log_method)
    setattr(logger.__class__, log_method, patch(method))


def log_format(record: dict[str, str | dict | int]) -> str:
    """
    format the log message with the string 'format_'
    """
    format_ = 'time={time}   loglevel={level}   filename={name}   line={line}   message="{message}"   '

    for key in ["requestID", "workflowType", "workflowID", "workflowRunID", "traceID", "spanID"]:
        if record["extra"].get(key):
            format_ += f"{key}={{extra[{key}]}}   "

    return format_ + "\n"


def log_filter(record: dict) -> bool:
    """
    Filters out logs
    """
    message: str = record.get("message") or ""
    if message.startswith("OPTIONS") or message.__contains__("/metrics"):
        return False
    return True


def __disable_logging(name: str) -> None:
    """
    disable logging
    """
    __logger = logging.getLogger(name)
    __logger.disabled = True


def configure_logging() -> None:
    """
    Configure logging
    """
    __disable_logging("uvicorn.access")
    logger.remove()
    logger.add(sys.stderr, format=log_format, filter=log_filter, enqueue=True)


configure_logging()
