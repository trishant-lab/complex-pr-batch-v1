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

    spark_image: str = "registry.314ecorp.tech/spark:3.5.6"
    spark_network_name: str = "sparknet"
    spark_container_ip: str = ""
    spart_runner_host_ip: str = ""

    copy_ui_bundle: bool = True
    database_name: str = "muspell"
