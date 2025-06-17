import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import psutil
from defusedxml.xmlrpc import xmlrpc_client
from fastapi import FastAPI
from prometheus_client import CollectorRegistry, Gauge
from prometheus_client.exposition import choose_encoder
from starlette.requests import Request
from starlette.responses import Response
from supervisor.states import ProcessStates
from supervisor.xmlrpc import SupervisorTransport

from app.core.cli_settings import get_workers_config


class Exporter:
    def __init__(self: "Exporter") -> None:
        self.registry = CollectorRegistry(auto_describe=True)
        self.queue_cache = set()
        self.workers_count = Gauge(
            "running_workers_count",
            "Indicates all running workers.",
            ["workers"],
            registry=self.registry,
        )
        self.expected_workers_count = Gauge(
            "expected_workers_count",
            "Indicates all expected running workers.",
            ["workers"],
            registry=self.registry,
        )
        self.system_usage = Gauge(
            "memory_usage",
            "Indicates cli pod CPU and memory usage.",
            ["resource_type"],
            registry=self.registry,
        )
        _server = xmlrpc_client.ServerProxy(
            "http://localhost:9001/RPC2",
            transport=SupervisorTransport(None, None, "unix:///tmp/supervisor.sock"),
        )
        self.supervisor = _server.supervisor
        self._set_expected_workers_count()

    def _set_expected_workers_count(self: "Exporter") -> None:
        """
        Get the status of all processes managed by Supervisor
        """
        total_count: int = sum(items.count for _, items in get_workers_config().items())
        self.expected_workers_count.labels("workers").set(total_count)

    def _set_worker_status(self: "Exporter") -> None:
        """
        Get the status of all processes managed by Supervisor
        """
        worker_config = get_workers_config().keys()
        count = sum(
            1
            for process in self.supervisor.getAllProcessInfo()
            if process["state"] == ProcessStates.RUNNING and process["group"] in worker_config
        )
        self.workers_count.labels("workers").set(count)

    def _set_memory_usage(self: "Exporter") -> None:
        self.system_usage.labels("CPU").set(psutil.cpu_percent())
        self.system_usage.labels("Memory").set(psutil.virtual_memory()[2])

    def run(self: "Exporter") -> None:
        """
        Helper fn to run shell commands
        """
        self._set_worker_status()
        self._set_memory_usage()


exporter = Exporter()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """
    Lifespan for the exporter
    """
    # Startup
    task = asyncio.create_task(periodic_refresh())
    yield
    # Shutdown
    task.cancel()


async def periodic_refresh() -> None:
    """
    Periodic refresh for the exporter
    """
    while True:
        exporter.run()
        await asyncio.sleep(1)


fastapi_app = FastAPI(lifespan=lifespan)

# disable access logs
__logger = logging.getLogger("uvicorn.access")
__logger.disabled = True


@fastapi_app.get("/metrics/")
async def get_metrics(request: Request) -> Response:
    """
    returns prometheus metrics
    """
    encoder, content_type = choose_encoder(request.headers.get("accept"))
    return Response(content=encoder(exporter.registry), headers={"Content-Type": content_type})
