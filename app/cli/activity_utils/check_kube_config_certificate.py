import base64
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pydash
import yaml
from cryptography.hazmat.backends import default_backend
from cryptography.x509 import load_pem_x509_certificate
from loguru import logger

from app.cli.temporal.core.exceptions import NonRetryableException
from app.utils.file_operations import get_opendal_file_client
from app.core.settings import get_settings
from app.mail_templates.main import kube_config_expiry_mail
from app.sendgrid_utils import send_mail

APPLICATION_CONFIG = get_settings()


async def check_kube_config_certificate_expiry() -> None:
    """
    check kube config certificate expiry and send mail if it is expired within one week
    """
    path: str = os.path.join(str(Path.home()), APPLICATION_CONFIG.kube_config_path)
    if not os.path.isfile(path):
        msg = f"File not found at path - {path}"
        raise NonRetryableException(msg)
    opendal_file_operations = get_opendal_file_client()
    file_content = await opendal_file_operations.read_file(path)
    _y = yaml.safe_load(file_content)
    cert_data = pydash.get(_y, "users.0.user.client-certificate-data")
    cert_bytes = base64.b64decode(cert_data)
    load_pem_x509_certificate(cert_bytes, default_backend())
    certificate = load_pem_x509_certificate(cert_bytes, default_backend())
    expiry_date: datetime = certificate.not_valid_after_utc
    _now = datetime.now(tz=UTC)
    logger.info(f"Kube Config Certificate Expires in: {(expiry_date - _now).days} days")
    if expiry_date <= _now + timedelta(days=7):
        await send_expiry_mail(expiry_date)


async def send_expiry_mail(expiry_date: datetime) -> None:
    """
    send expiry mail
    """
    if APPLICATION_CONFIG.is_env_integration:
        env = "Integration"
    else:
        env = "Production"
    subject = f"[Launchpad-{env}] - Kube Config Certificate Expiration Warning!"
    content = kube_config_expiry_mail(expiry_date=expiry_date)
    await send_mail(
        to_email=APPLICATION_CONFIG.sendgrid.support_mail,
        subject=subject,
        content=content,
        from_name="Launchpad",
        email_from=APPLICATION_CONFIG.sendgrid.email_from,
    )
