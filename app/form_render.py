import os
import subprocess
import tempfile

import orjson

from app.core.db import DBManager, get_db_manager
from app.core.settings import AppSettings, get_settings

SCRIPT_PATH: str = os.path.join(os.path.join(os.path.dirname(__file__), "../formrender/formRender.js"))


def render_form(tmp_dir: str) -> dict:
    """
    :param tmp_dir:
    :return:
    """
    form_path = os.path.join(tmp_dir, "form/source")
    i18n_path = os.path.join(tmp_dir, "i18n")
    html_render_path = os.path.join(tmp_dir, "form/html_render")

    os.makedirs(html_render_path, exist_ok=True)
    args_ = ["node", SCRIPT_PATH, f"inputDir={form_path}", f"outputDir={html_render_path}", f"i18Path={i18n_path}"]
    subprocess.run(args_, check=True)

    with open(os.path.join(html_render_path, "form.json")) as f:
        return orjson.loads(f.read())


async def form_render_for_product(product: str) -> dict:
    """
    :return:
    """
    config: AppSettings = get_settings()
    db: DBManager = await get_db_manager(config.postgres.dsn)

    response = await db.fetch_one("getProductSchema.sql", product=product)

    tmp_dir: str = tempfile.gettempdir()

    os.makedirs(os.path.join(tmp_dir, "form/source"), exist_ok=True)
    os.makedirs(os.path.join(tmp_dir, "i18n"), exist_ok=True)
    os.makedirs(os.path.join(tmp_dir, "form/html_render"), exist_ok=True)

    with open(os.path.join(tmp_dir, "form/source/form.json"), "w") as f:
        f.write(response["product_schema"])

    return render_form(tmp_dir)
