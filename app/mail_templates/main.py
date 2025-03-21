import os

from asyncpg import Record
from jinja2 import Environment, FileSystemLoader
from pendulum import Date

from app.core.settings import get_settings
from app.models.enums import SubscriptionType
from app.models.lago.customer import CustomerResponse
from app.models.product import ProductEnum

settings = get_settings()

# Set variables for links and contact info

# Load the Jinja template file
env = Environment(
    loader=FileSystemLoader(os.path.join(os.path.abspath(os.path.dirname(__file__)), "templates")),
    autoescape=True,
)


def provisioning_success_mail(name: str, email: str, link: str, password: str, product: ProductEnum) -> str:
    """
    @param name:
    @param email:
    @param link:
    @param password:
    @return:
    """
    match product:
        case ProductEnum.veritable:
            template = env.get_template("veritable/provisioning_success_mail.html")
            return template.render(
                user_name=name,
                email=email,
                environment_link=link,
                support_email=settings.veritable.sendgrid.support_mail,
                password=password,
            )
        case _:
            raise ValueError(f"Not Implemented for product: {product.value}")


def otp_verification_mail(otp: int, plan_name: str, product: ProductEnum) -> str:
    """
    @param otp:
    @param plan_name:
    @return:
    """
    match product:
        case ProductEnum.veritable:
            template = env.get_template("veritable/otp_verification_mail.html")
            return template.render(
                otp=otp,
                plan_name=plan_name,
                expiry_minutes=settings.redis.otp_expiration // 60,
                support_email=settings.veritable.sendgrid.support_mail,
            )
        case _:
            raise ValueError(f"Invalid product: {product}")


def periodic_invoice_mail(
    product: ProductEnum,
    name: str,
    plan_name: str,
    plan_interval: str,
    renew_date: Date,
    subscription_type: SubscriptionType,
    tenant_link: str | None,
) -> str:
    """
    @param name:
    @param plan_name:
    @param plan_interval:
    @param renew_date:
    @param subscription_type:
    @param tenant_link:
    @return:
    """
    match product:
        case ProductEnum.veritable:
            match subscription_type:
                case SubscriptionType.renewal:
                    template = env.get_template("veritable/periodic_invoice_mail.html")
                case SubscriptionType.upgrade:
                    template = env.get_template("veritable/plan_upgrade_invoice_mail.html")
                case SubscriptionType.initial:
                    template = env.get_template("veritable/payment_success.html")
                case _:
                    return ""
            return template.render(
                user_name=name,
                plan_name=plan_name,
                plan_interval=plan_interval,
                renew_date=renew_date,
                support_email=settings.veritable.sendgrid.support_mail,
                tenant_link=tenant_link,
            )
        case _:
            raise ValueError(f"Not Implemented for product: {product.value}")


def internal_payment_failure_mail(customer: CustomerResponse, product: ProductEnum) -> str:
    """
    @param customer:
    @param product:
    @return:
    """
    match product:
        case ProductEnum.veritable:
            template = env.get_template("veritable/internal_payment_failure_mail.html")
            return template.render(
                customer_phone=customer.phone or "",
                customer_email=customer.email,
                customer_name=customer.name or "",
            )
        case _:
            raise ValueError(f"Not Implemented for product: {product.value}")


def internal_renewal_payment_failure_mail(customer: CustomerResponse, tenant_name: str, product: ProductEnum) -> str:
    """
    @return:
    """
    match product:
        case ProductEnum.veritable:
            template = env.get_template("veritable/internal_renewal_payment_failure_mail.html")
            return template.render(
                customer_phone=customer.phone or "",
                customer_email=customer.email,
                customer_name=customer.name or "",
                tenant_name=tenant_name,
            )
        case _:
            raise ValueError(f"Not Implemented for product: {product.value}")


def payment_failure_mail(name: str, retry_link: str, plan_name: str, product: ProductEnum) -> str:
    """
    @param name:
    @param retry_link:
    @param plan_name:
    @return:
    """
    match product:
        case ProductEnum.veritable:
            template = env.get_template("veritable/payment_failure_mail.html")
            return template.render(
                user_name=name,
                payment_link=retry_link,
                plan_name=plan_name,
                support_email=settings.veritable.sendgrid.support_mail,
            )
        case _:
            raise ValueError(f"Not Implemented for product: {product.value}")


def provisioning_failure_mail(name: str, plan_name: str, product: ProductEnum) -> str:
    """
    @param name:
    @param plan_name:
    @return:
    """
    match product:
        case ProductEnum.veritable:
            template = env.get_template("veritable/provisioning_failure_mail.html")
            return template.render(
                user_name=name, plan_name=plan_name, support_email=settings.veritable.sendgrid.support_mail
            )
        case _:
            raise ValueError(f"Not Implemented for product: {product.value}")


def sign_in_detected(name: str, env_link: str, product: ProductEnum) -> str:
    """
    @param name:
    @param env_link:
    @return:
    """
    match product:
        case ProductEnum.veritable:
            template = env.get_template("veritable/signin_detected.html")
            return template.render(
                user_name=name,
                environment_link=env_link,
                support_email=settings.veritable.sendgrid.support_mail,
            )
        case _:
            raise ValueError(f"Not Implemented for product: {product.value}")


def tenant_link_mail(tenant_links: list[Record], product: ProductEnum) -> str:
    """
    @param tenant_links:
    @return:
    """
    match product:
        case ProductEnum.veritable:
            template = env.get_template("veritable/tenant_link_mail.html")
            return template.render(
                tenant_links=tenant_links,
                support_email=settings.veritable.sendgrid.support_mail,
            )
        case _:
            raise ValueError(f"Not Implemented for product: {product.value}")
