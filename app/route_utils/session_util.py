import random
import secrets
import string
import uuid

from pydantic import EmailStr

from app.core.connections import get_lago_client
from app.core.db import DBManager
from app.core.settings import get_settings
from app.mail_templates.main import sign_in_detected
from app.models.billing_models import OnboardingResponseModel
from app.models.enums import OnboardingStatus
from app.models.lago.customer import Customer
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum
from app.sendgrid_utils import send_mail

system_random = random.SystemRandom()
ALPHABET = string.digits + string.ascii_letters
settings = get_settings()


def get_treated_email(email: EmailStr) -> EmailStr:
    """
    @param email:
    @return:
    """
    email = email.lower()
    if email.split("@")[1] == "314ecorp.com":
        return email
    return email.split("+")[0] + "@" + email.split("@")[1] if "+" in email else email


def _get_hashed_key(product: ProductEnum, key: EmailStr, hash_key: uuid.UUID) -> str:
    return uuid.uuid5(hash_key, product.value + get_treated_email(key)).__str__().replace("-", "")


def _generate_password(pwd_len: int, conditions: list[tuple[str, int]], pwd_charset: str) -> str:
    """
    Generates a password based on specified conditions.

    @param pwd_len:
        The desired length of the password.
    @param conditions:
        A list of tuples, where each tuple contains a character set,
        and the minimum number of characters to include from that set.
    @param pwd_charset:
        Additional character set to use for password generation.

    @return: A string representing the generated password.
    """
    charsets = set(pwd_charset)

    password = []
    for charset, min_count in conditions:
        if not charset:
            msg = f"Invalid character set: {charset}"
            raise ValueError(msg)
        charsets.update(charset)
        password.extend(secrets.choice(charset) for _ in range(min_count))

    if len(password) >= pwd_len:
        msg = "Conditions length is greater than desired password length"
        raise ValueError(msg)

    unified_charset = "".join(charsets)
    remaining_chars = pwd_len - len(password)

    password.extend(secrets.choice(unified_charset) for _ in range(remaining_chars))

    system_random.shuffle(password)
    return "".join(password)


def generate_password(pwd_length: int) -> str:
    """
    @param pwd_length:
    @param charset:
    @return:
    """
    conditions = [
        (string.ascii_uppercase, 1),
        (string.ascii_lowercase, 1),
        (string.digits, 1),
    ]
    return _generate_password(pwd_length, conditions, ALPHABET)


def get_customer_tenant_details(product: ProductEnum) -> tuple[str, str]:
    """
    Returns tenant fqdn, email_from for product
    """
    match product:
        case ProductEnum.veritable:
            return settings.veritable.tenant_fqdn, settings.veritable.sendgrid.email_from
        case _:
            raise ValueError(f"No tenant fqdn for product {product}")


async def get_first_subscription_status(
    email: EmailStr,
    db: DBManager,
    product: ProductEnum,
) -> tuple[OnboardingResponseModel | None, dict | None]:
    """
    @param email:
    @param db:
    @return:
    """
    customer_params = {
        "email": email,
        "product": product.value,
    }
    customer_record = await db.fetch_one("get_subscription_status.sql", **customer_params)
    if customer_record:
        customer_record = dict(customer_record)
        customer_record = customer_record | dict(
            await db.fetch_one(
                "get.sql",
                table="provisioningstatus",
                where=f"customerid='{customer_record['id']}'",
                columns=["status"],
            ),
        )
        provisioning_status = TenantStatusEnum(customer_record["status"])
        if provisioning_status == TenantStatusEnum.Provisioned:
            tenant_fqdn, email_from = get_customer_tenant_details(product)
            tenantname = customer_record["tenantname"]
            customer_domain = f"https://{tenantname}.{tenant_fqdn}"
            lago_client = get_lago_client(product)
            customer_resp = lago_client.customers().find(str(customer_record["id"]))
            customer = Customer.from_lago(customer_resp)
            mail_content = sign_in_detected(name=customer.name, env_link=customer_domain, product=product)
            await send_mail(
                to_email=customer_record["email"],
                email_from=email_from,
                subject=f"Sign-in detected - {product.value}",
                content=mail_content,
                from_name=f"{product.value}",
            )
            return OnboardingResponseModel(status=OnboardingStatus.PROVISIONED, domain=customer_domain), None
        if provisioning_status in {
            TenantStatusEnum.Provisioning,
            TenantStatusEnum.Failed,
        }:
            return OnboardingResponseModel(status=OnboardingStatus.IN_PROGRESS), None
    return None, customer_record
