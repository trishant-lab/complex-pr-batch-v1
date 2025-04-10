from typing import Any, ClassVar

import phonenumbers
from better_profanity import profanity
from pydantic import BaseModel, EmailStr, Field, GetCoreSchemaHandler, ValidationError, field_validator, model_validator
from pydantic_core import CoreSchema, core_schema

from app.core.ijson import ijson_loads
from app.exceptions import errors
from app.models.enums import AddOn, BillingTime, OnboardingStatus, PaymentStatus, Provider
from app.models.input_param_patterns import TENANT_NAME_PATTERN
from app.models.lago.customer import Customer, CustomerBillingConfiguration
from app.models.lago.invoice import InvoiceResponse
from app.models.lago.plan import PlanResponse
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum

COUNTRY_CODES = ["US", "IN", "CA", "MX"]
RESERVED_TENANT_NAMES = {"auth", "accounts", "get"}


class PhoneNumber(str):
    """Phone Number Pydantic type, using google's phonenumbers"""

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _handler: GetCoreSchemaHandler,
        _source_type: Any | None = None,
    ) -> CoreSchema:
        """Define the core schema for phone number validation"""
        return core_schema.str_schema(serialization=core_schema.plain_serializer_function_ser_schema(cls.validate))

    @classmethod
    def validate(cls: "PhoneNumber", v: str) -> "PhoneNumber":
        """
        Remove spaces
        @param v:
        @return:
        """
        v = v.strip().replace(" ", "")

        try:
            pn = phonenumbers.parse(v)
        except phonenumbers.phonenumberutil.NumberParseException:
            raise errors.INVALID_PHONE_NUMBER.exc()

        return cls(phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.E164))


class CustomerResponseModel(Customer):
    plancode: str
    email: EmailStr
    tenant_name: str | None = Field(pattern=TENANT_NAME_PATTERN)

    model_config: ClassVar[dict] = {"extra": "allow"}  # allow extra fields from database


class OnboardingStage(BaseModel):
    invoice: InvoiceResponse | None = None
    provisioningStatus: TenantStatusEnum | None = None
    paymentStatus: PaymentStatus | None = None
    failedInvoiceReason: dict[str, Any] | None = None


class OnboardingResponseModel(BaseModel):
    status: OnboardingStatus | None = None
    onboardingStage: OnboardingStage | None = None
    domain: str | None = None
    clientSecret: str | None = None
    sessionToken: str | None = None
    customer: CustomerResponseModel | None = None


class AddOnResponseModel(BaseModel):
    name: str
    code: AddOn
    description: str
    features: list[str]
    price: float
    sortorder: int
    marketingType: int

    @staticmethod
    def json_to_model(data: dict) -> "AddOnResponseModel":
        """
        @param data:
        @return:
        """
        if isinstance(data["details"], str):
            data["features"] = ijson_loads(data["details"])

        from app.route_utils.addons_util import get_addon_name, get_addon_price

        product = ProductEnum(data["product"])
        data["name"] = get_addon_name(product, data["code"])
        data["price"] = get_addon_price(product, data["code"], data["plancode"])
        data["code"] = ProductEnum.get_add_on_enum(product)(data["code"])
        return AddOnResponseModel.model_validate(data)


class PlanModel(PlanResponse):
    features: list[str]
    popular: bool | None
    addons: list[AddOnResponseModel]

    @staticmethod
    def json_to_model(data: dict) -> "PlanModel":
        """
        @param data:
        @return:
        """
        data["addons"] = [AddOnResponseModel.json_to_model(addon) for addon in data["addons"]]
        return PlanModel.model_validate(data)


class PlanResponseModel(BaseModel):
    monthly: list[PlanModel]
    yearly: list[PlanModel]


class CustomCustomerBillingConfiguration(CustomerBillingConfiguration):
    payment_provider: str = Field(default=Provider.STRIPE.value)
    sync: bool | None = Field(default=True)
    sync_with_provider: bool = Field(default=True)


class CustomerModel(Customer):
    external_id: str | None = None
    email: EmailStr
    tenant: str | None = Field(pattern=TENANT_NAME_PATTERN)
    billing_configuration: CustomCustomerBillingConfiguration = CustomCustomerBillingConfiguration()
    phone: PhoneNumber | None = None
    legal_name: str
    coupon_code: str | None = None

    @field_validator("tenant")
    @classmethod
    def validate_tenant_name(cls: "CustomerModel", tenant: str | None) -> str | None:
        """
        @param tenant:
        @return:
        """
        if tenant is None:
            return None

        if tenant.lower() in RESERVED_TENANT_NAMES:
            raise ValueError("Invalid tenant name!")

        if profanity.contains_profanity(tenant):
            raise ValueError("Explicit words are not allowed!")
        return tenant

    @field_validator("country")
    @classmethod
    def validate_country(cls: type["CustomerModel"], country: str) -> str:
        """
        @param country:
        @return:
        """
        if country not in COUNTRY_CODES:
            raise ValidationError(
                [
                    (
                        ValueError(f"Invalid country code! Allowed values - {COUNTRY_CODES}"),
                        "country",
                    ),
                ],
                CustomerModel,
            )
        return country

    @model_validator(mode="before")
    @classmethod
    def set_url(cls: type["CustomerModel"], values: dict) -> dict:
        """
        set url based on tenant name
        """
        tenant = values.get("tenant")
        if tenant:
            app_config = ProductEnum.get_product_settings(values.get("product"))
            values["url"] = f"https://{tenant}.{app_config.tenant_fqdn}"

        return values


class CustomerInputModel(CustomerModel):
    country: str
    state: str


class CustomerPatchModel(Customer):
    name: str | None


class SubscriptionModel(BaseModel):
    plan_code: str
    name: str | None
    payment_method_id: str | None = None
    email: EmailStr
    billing_time: BillingTime | None
    external_customer_id: str | None
    external_id: str | None
