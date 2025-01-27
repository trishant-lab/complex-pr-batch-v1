from functools import lru_cache

import jinja2


@lru_cache
def get_env(template_path: str) -> jinja2.Environment:
    """
    Sets up jinja2 environment using file loader
    :param template_path:
    :return:
    """
    loader: jinja2.FileSystemLoader = jinja2.FileSystemLoader(template_path)
    return jinja2.Environment(
        loader=loader,
        trim_blocks=True,
        autoescape=True,
        keep_trailing_newline=True,
        variable_start_string="<<",
        variable_end_string=">>",
    )
