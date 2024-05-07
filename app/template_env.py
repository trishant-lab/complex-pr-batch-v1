from functools import lru_cache
from os import path

import jinja2


@lru_cache()
def get_env(product: str) -> jinja2.Environment:
    """
    Sets up jinja2 environment using file loader
    :param product:
    :type product:
    :return:
    :rtype:
    """
    template_path = path.abspath(path.join(
        path.dirname(__file__), f"temporal/{product}/templates")
    )
    loader: jinja2.FileSystemLoader = jinja2.FileSystemLoader(template_path)
    env: jinja2.Environment = jinja2.Environment(
        loader=loader, trim_blocks=True, autoescape=False,
        keep_trailing_newline=True, extensions=["jinja2.ext.do", ]
    )
    env.globals.update(open_brackets='{{', close_brackets='}}')

    return env
