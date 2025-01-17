import base64
import os
from datetime import datetime, UTC
from collections.abc import Callable
from typing import ClassVar

import python_http_client.exceptions as sg_exceptions
import aiohttp
from sendgrid import (
    SendGridAPIClient,
    Attachment,
    Mail,
    From,
    To,
    Content,
    CustomArg,
    Subject,
    FileContent,
    Disposition,
    FileType,
    FileName,
    Personalization,
    Bcc,
)

TEXT_HTML_MIME_TYPE = "text/html"

from app.core.settings import get_settings, AppSettings
from app.models.mail import SGMailStatus, CommunicationMedium, MessageProvider

config: AppSettings = get_settings()


class Singleton(type):
    _instances: ClassVar[dict] = {}

    def __call__(cls: "Singleton", *args: any, **kwargs: any) -> any:
        """
        @param args:
        @param kwargs:
        @return:
        """
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class SendgridMailException(Exception):
    """
    Exception indicating one of
    400 Bad request
    401	Requires authentication
    403	From address doesn't match Verified Sender Identity.
    413 Mail body too large
    429	Too many requests/Rate limit exceeded
    """

    pass


class SendgridServerException(Exception):
    """
    Exception indicating sendgrid server error
    """

    pass


class Sendgrid(metaclass=Singleton):
    def __init__(self: "Sendgrid") -> None:
        self.sendgrid_config = config.sendgrid
        self.sg = SendGridAPIClient(api_key=self.sendgrid_config.api_key)

    def prepare_mail(
        self: "Sendgrid",
        subject: str,
        content: str,
        email_from: str,
        to_email: str | list | None = None,
        bcc_email: str | list | None = None,
        attachments: list[Attachment] | None = None,
        from_name: str | None = None,
        mime_type: str = TEXT_HTML_MIME_TYPE,
    ) -> Mail:
        """
        @param to_email:
        @param subject:
        @param content:
        @param email_from:
        @param attachments:
        @param from_name:
        @param mime_type:
        @param bcc_email:
        @return:
        """
        mail: Mail = Mail()
        if isinstance(to_email, str):
            to_email = [to_email]

        # Add personalization for each recipient
        for recipient in to_email:
            personalization = Personalization()
            personalization.add_to(To(recipient))
            mail.add_personalization(personalization)

        mail.from_email = From(email=email_from, name=from_name)
        mail.subject = Subject(subject=subject)
        mail.content = [Content(mime_type=mime_type, content=content)]
        if bcc_email:
            if isinstance(bcc_email, str):
                bcc_email = [bcc_email]
            mail.bcc = [Bcc(email=email) for email in bcc_email]
        if self.sendgrid_config.category:
            mail.custom_arg = CustomArg(key="cid", value=self.sendgrid_config.category)
        if attachments:
            [mail.add_attachment(attachment) for attachment in attachments]
        return mail

    @staticmethod
    def __make_request(fn: Callable, *args: any, **kwargs: any) -> any:
        ignore_sg_request: bool = False
        if "ignore_sg_request" in kwargs:
            ignore_sg_request = kwargs.pop("ignore_sg_request")
        try:
            return fn(*args, *kwargs)
        except (
            sg_exceptions.BadRequestsError,
            sg_exceptions.UnauthorizedError,
            sg_exceptions.ForbiddenError,
            sg_exceptions.PayloadTooLargeError,
        ) as e:
            # 401
            # API key error
            raise SendgridMailException(e)
        except sg_exceptions.TooManyRequestsError as e:
            # 429
            # too many requests, ignoring while checking mail status
            if not ignore_sg_request:
                raise SendgridMailException(e)
        except sg_exceptions.InternalServerError as e:
            # 500
            # sendgrid error
            raise SendgridServerException(e)

    def get_pending_messages(self: "Sendgrid", params: dict) -> list:
        """
        @param params:
        @return:
        """
        response = self.__make_request(
            self.sg.client.messages.get,
            query_params=params,
            ignore_sg_request=True,
        )
        if response:
            return response.to_dict.get("messages", [])
        return []

    def send_mail(
        self: "Sendgrid",
        subject: str,
        content: str,
        from_name: str,
        email_from: str,
        to_email: str | list | None = None,
        bcc_email: str | list | None = None,
        attachments: list | None = None,
        mime_type: str = TEXT_HTML_MIME_TYPE,
    ) -> dict:
        """
        @param to_email:
        @param bcc_email
        @param subject:
        @param content:
        @param from_name:
        @param email_from:
        @param attachments:
        @param mime_type:
        @return:
        """
        mail = self.prepare_mail(
            to_email=to_email,
            bcc_email=bcc_email,
            subject=subject,
            content=content,
            from_name=from_name,
            email_from=email_from,
            mime_type=mime_type,
            attachments=attachments,
        )
        response = self.__make_request(self.sg.send, mail)
        return {
            "msgid": response.headers.get("X-Message-Id"),
            "status": SGMailStatus.processing.value,
            "medium": CommunicationMedium.email.value,
            "provider": MessageProvider.sendgrid.value,
            "msgto": to_email,
            "msgfrom": self.sendgrid_config.email_from,
            "created": datetime.now(UTC),
            "responseStatus": response.status_code,
        }


sendgrid = Sendgrid()


async def send_mail(
    subject: str,
    content: str,
    from_name: str,
    email_from: str,
    to_email: str | list | None = None,
    bcc_email: str | list | None = None,
    attachments: list | None = None,
    attachment_with_url: bool = False,
    mime_type: str = TEXT_HTML_MIME_TYPE,
) -> dict[str, datetime | str]:
    """
    @param to_email:
    @param bcc_email:
    @param subject:
    @param content:
    @param from_name:
    @param email_from:
    @param attachments:
    @param attachment_with_url:
    @param mime_type:
    @return:
    """
    if attachment_with_url:
        attachments = await fetch_and_set_attachments(attachments=attachments)
    return sendgrid.send_mail(
        subject=subject,
        content=content,
        from_name=from_name,
        email_from=email_from,
        to_email=to_email,
        bcc_email=bcc_email,
        attachments=attachments,
        mime_type=mime_type,
    )


async def fetch_and_set_attachments(attachments: list) -> list[Attachment]:
    """
    @param attachments:
    @return:
    """
    attaches = []
    for attachment in attachments:
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment, timeout=60) as response:
                file_content = base64.b64encode(await response.content.read()).decode("utf-8")
                file_name = os.path.basename(attachment)
        file_type = "application/pdf"  # Adjust the MIME type according to your attachment

        attachment = Attachment()
        attachment.file_content = FileContent(file_content)
        attachment.file_name = FileName(file_name)
        attachment.file_type = FileType(file_type)
        attachment.disposition = Disposition("attachment")
        attaches.append(attachment)
    return attaches
