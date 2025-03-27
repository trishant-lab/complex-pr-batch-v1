from pydantic import BaseModel


class PractiflySettings(BaseModel):
    """
    Practifly Settings
    """

    zone_id: str = ""
    domain_name: str = "practifly.tech"
    sender_name: str = ""
    sender_email: str = ""
    email_domains_exclusions: list[str] = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com"]
