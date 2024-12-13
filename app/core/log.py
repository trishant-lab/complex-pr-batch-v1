import os
import sys
from collections.abc import Callable
from typing import Any

from loguru import Logger, logger


def patch(logger_method: Callable) -> Callable:
    """
    function extends loguru internal function to bind kwargs to extra parameter
    kwargs   :   key word args passed at the time of logging , all parameters except message
    """

    def patched(self: Logger, message: str, *args: Any, **kwargs: Any) -> None:
        self = self.opt(depth=1).bind(**kwargs)
        logger_method(self, message, *args, **kwargs)

    return patched


for log_method in ("trace", "debug", "info", "error", "warning", "critical"):
    method = getattr(logger.__class__, log_method)
    setattr(logger.__class__, log_method, patch(method))


def format(record) -> str:  # noqa ANN001, loguru.Record
    """
    format the log message with the string 'format_'
    """
    format_ = 'time={time}   loglevel={level}   filename={name}   line={line}   message="{message}"  '
    if "action" in record["extra"].keys():
        format_ += 'action="{extra[action]}"  '
    if "status" in record["extra"].keys():
        format_ += 'status="{extra[status]}"  '
    if "detail" in record["extra"].keys():
        format_ += 'detail="{extra[detail]}"  '
    if "exception" in record["extra"].keys():
        format_ += 'exception="{extra[exception]}"  '
    for keys in record["extra"].keys():
        if keys not in {"action", "status", "detail", "exception"}:
            format_ += f'{keys}="{{extra[{keys}]}}"   '
    return format_ + "\n"


logger.remove()
logger.add(sys.stderr, format=format)


def setup_logging(log_dir: str, log_file_path: str) -> None:
    """
    log file handler to the sink location
    rotation   :  time of new file creation
    format     :  format of the log message
    log_file_path: path of the log file to be stored
    """
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)

    logger.add(sink=log_file_path, rotation="00:00", format=format)
