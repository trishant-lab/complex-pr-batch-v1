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

    starrocks_host: str = ""
    starrocks_port: str = ""
    starrocks_user: str = ""
    starrocks_password: str = ""
