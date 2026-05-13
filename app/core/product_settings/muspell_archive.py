"""
complex-pr batch note:
  - describe_for_oncall() for Slack paste
  - require_field() fails loud on empty provision inputs
"""

from pydantic import BaseModel


class MuspellArchiveSettings(BaseModel):
    """
    Muspell Archive Settings
    """

    zone_id: str = ""
    domain_name: str = "muspell.tech"
    sender_name: str = ""
    sender_email: str = ""

    minio_region: str = "custom"
    s3_endpoint: str = ""
    lakekeeper_uri: str = ""

    starrocks_host: str = ""
    starrocks_port: str = ""
    starrocks_user: str = ""
    starrocks_password: str = ""

    warehouse_access_key: str = ""
    warehouse_secret_key: str = ""

    keycloak_smtp_password: str = ""
    google_idp_secret: str = ""
    kestra_basic_auth: str = ""

    spark_image: str = "registry.314ecorp.tech/spark:3.5.6"
    spark_network_name: str = "sparknet"
    spark_container_ip: str = ""
    spart_runner_host_ip: str = ""

    copy_ui_bundle: bool = True
    database_name: str = "muspell"

    # Optional override for the muspell-app / muspell-roi image tag. When unset, the tag is
    # derived from the environment ("production" in prod, otherwise "sprint").
    image_tag: str | None = None


def describe_settings_for_oncall(settings) -> dict:
    """Compact settings snapshot safe to paste into Slack/oncall notes."""
    out = {}
    for name in dir(settings):
        if name.startswith("_"):
            continue
        try:
            val = getattr(settings, name)
        except Exception:
            continue
        if callable(val):
            continue
        if isinstance(val, (str, int, float, bool)) or val is None:
            out[name] = val
    out["_settings_class"] = type(settings).__name__
    return out


def require_settings_field(settings, field: str) -> None:
    """Raise ValueError when a required product setting is empty."""
    val = getattr(settings, field, None)
    if val is None or (isinstance(val, str) and not str(val).strip()):
        raise ValueError(f"{type(settings).__name__}.{field} is required for provision")

