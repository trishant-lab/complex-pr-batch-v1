import json
import os
import shutil
from configparser import ConfigParser

import app
from app.core.cli_settings import get_workers_config
from app.core.settings import CONFIG_FILE_NAMES


def get_config_env_dict() -> dict:
    """
    get config env dict
    """
    config_dir = os.getenv("APP_CONFIG_DIR", "/")
    config_files = [x.path for x in os.scandir(config_dir) if x.name in CONFIG_FILE_NAMES and "settings" in x.name]
    return json.loads(open(config_files[0]).read()) if config_files else {}


def write_supervisor_workers_conf() -> None:
    """
    write supervisor workers config
    """
    cwd: str = os.path.join(os.path.abspath(os.path.dirname(app.__file__)), "..")
    python_path: str = shutil.which("python3") or "python3"
    file_path: str = os.path.join(os.path.abspath(os.path.dirname(__file__)), "workersd.conf")

    from app.cli.temporal import worker

    worker_runner = os.path.abspath(worker.__file__)

    common_config_dict: dict = {
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

    with open(file_path, "w") as configfile:
        worker_config.write(configfile)


if __name__ == "__main__":
    write_supervisor_workers_conf()
