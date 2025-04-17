import json
from os import environ
from os.path import abspath, dirname, join

from fastapi.openapi.utils import get_openapi

if environ.get("APP_CONFIG_DIR", None):
    environ["APP_CONFIG_DIR"] = "/"

from app.core.cli_settings import get_workers_config


def openapi_3_0_1() -> dict:
    """
    Returns openapi version 3.0.1
    """
    from app.main import fastapi_app

    return get_openapi(title="Launchpad APP", version="0.1.0", openapi_version="3.0.1", routes=fastapi_app.routes)


if __name__ == "__main__":
    with open(join(dirname(abspath(__file__)), "../openapi.json"), "w") as f:
        json.dump(openapi_3_0_1(), f, indent=2)
    get_workers_config()
