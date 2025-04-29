import asyncio
import secrets
import string
from collections.abc import Callable
from typing import Any


def generate_password(length: int) -> str:
    """
    :param length:
    :return:
    """
    all_characters = string.ascii_letters + string.digits
    return "".join(secrets.choice(all_characters) for _ in range(length))


def run_async_task(func: Callable, *args: Any, **kwargs: Any) -> Any:
    """
    Run a task
    """
    try:
        loop = asyncio.get_running_loop()
        future = asyncio.run_coroutine_threadsafe(func(*args, **kwargs), loop)
        return future.result()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(func(*args, **kwargs))
