from pydantic import BaseModel


class PractiflySettings(BaseModel):
    """
    Practifly Settings
    """

    zone_id: str = ""
    domain_name: str = "practifly.tech"
    sender_name: str = ""
    sender_email: str = ""
