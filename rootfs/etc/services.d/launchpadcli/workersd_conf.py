import os
import shutil
from configparser import ConfigParser

import app
from app.common import run_async_task
from app.core.cli_settings import get_workers_config
from app.core.ijson import ijson_dumps, ijson_loads
from app.core.settings import CONFIG_FILE_NAMES
from app.utils.file_operations import get_opendal_file_client


async def get_config_env_dict() -> dict:
    """
    get config env dict
    """
    opendal_file_operations = get_opendal_file_client()
    config_dir = os.getenv("APP_CONFIG_DIR", "/")
    config_files = [x.path for x in os.scandir(config_dir) if x.name in CONFIG_FILE_NAMES and "settings" in x.name]
    return ijson_loads(await opendal_file_operations.read_file(config_files[0])) if config_files else {}


async def write_supervisor_workers_conf() -> None:
    """
    write supervisor workers config
    """
    cwd: str = os.path.join(os.path.abspath(os.path.dirname(app.__file__)), "..")
    python_path: str = shutil.which("python3") or "python3"
    uvicorn_path: str = shutil.which("uvicorn") or "uvicorn"
    file_path: str = os.path.join(os.path.abspath(os.path.dirname(__file__)), "workersd.conf")

    from app.cli.temporal import worker

    worker_runner = os.path.abspath(worker.__file__)

    common_config_dict: dict[str, str | bool | int] = {
        "directory": cwd,
        "autostart": True,
        "autorestart": True,
        "startsecs": 10,
        "stopwaitsecs": 600,
        "priority": 1000,
    }
    worker_config = ConfigParser(interpolation=None)
    for worker_process, items in get_workers_config().items():
        key = f"program:{worker_process}"
        value = {
            "command": f"{python_path} {worker_runner} --process {worker_process}",
            "stopasgroup": True,
            "numprocs": items.count,
            "process_name": f"launchpad_{worker_process}_%(process_num)02d",
            **common_config_dict,
        }
        worker_config[key] = value

    worker_config["program:monitoring"] = {
        "command": f"{uvicorn_path} app.cli.exporter:fastapi_app --port 8000 --host 0.0.0.0",
        "stopasgroup": False,
        "numprocs": 1,
        "process_name": "launchpad_worker_monitoring_%(process_num)02d",
        **common_config_dict,
    }

    opendal_file_operations = get_opendal_file_client()
    await opendal_file_operations.write_file(file_path, ijson_dumps(worker_config))


if __name__ == "__main__":
    run_async_task(write_supervisor_workers_conf())
