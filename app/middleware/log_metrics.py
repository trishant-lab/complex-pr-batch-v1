import time
from uuid import uuid4

from loguru import logger
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class LoggerMiddleware:
    def __init__(self: "LoggerMiddleware", app: ASGIApp) -> None:
        self.app = app

    async def __call__(self: "LoggerMiddleware", scope: Scope, receive: Receive, send: Send) -> None:
        """
        Loguru middleware
        - Add request ID to the response headers
        - Log the request method, path, and elapsed time
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid4())
        start_time = time.perf_counter()

        # Create request to access state
        scope["request_id"] = request_id
        scope["start_time"] = start_time
        _response_status_code = None

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                nonlocal _response_status_code
                _response_status_code = message["status"]
                _request_header: tuple[bytes, bytes] = (b"x-request-id", request_id.encode())
                if message.get("headers"):
                    message["headers"].append(_request_header)
                else:
                    message["headers"] = [_request_header]
            await send(message)

        with logger.contextualize(requestID=request_id, startTime=start_time):
            await self.app(scope, receive, send_wrapper)
            elapsed = f"{round(time.perf_counter() - start_time, 4)}s"
            logger.debug(f"{scope['method']} {scope['path']} status_code={_response_status_code} {elapsed}")
