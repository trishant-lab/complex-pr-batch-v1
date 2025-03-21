from typing import Any, TypeVar

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from app.cli.temporal.penknife.models.penknife_spec import EmailProvider, TenantType
from app.models.billing_models import COUNTRY_CODES, CustomCustomerBillingConfiguration, PhoneNumber
from app.models.form_schema.base_schema import BaseFormSchema
from app.models.product import ProductEnum


class VeritableSchema(BaseFormSchema):
    billing_configuration: CustomCustomerBillingConfiguration = Field(
        default=CustomCustomerBillingConfiguration(),
        json_schema_extra={
            "name": "billingConfiguration",
            "label": "Billing Configuration",
            "className": "form-control",
            "subtype": "text",
            "mapTo": "billing_configuration",
            "order": 6,
        },
    )
    external_id: str | None = Field(
        default=None,
        json_schema_extra={
            "name": "externalId",
            "label": "External ID",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. e38c5f99-580b-4bfd-a926-a82402eb8d6a",
            "mapTo": "external_id",
            "order": 7,
        },
    )
    phone: PhoneNumber | None = Field(
        default=None,
        json_schema_extra={
            "name": "phoneNumber",
            "label": "Phone Number",
            "subtype": "number",
            "className": "form-control",
            "placeholder": "e.g. 1234567890",
            "mapTo": "phone",
            "order": 8,
        },
    )
    address_line1: str | None = Field(
        default=None,
        json_schema_extra={
            "name": "address",
            "label": "Address",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. 1234 Main St",
            "mapTo": "address_line1",
            "order": 9,
        },
    )
    city: str = Field(
        json_schema_extra={
            "name": "city",
            "label": "City",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. Berkeley",
            "mapTo": "city",
            "order": 10,
        },
    )
    state: str = Field(
        json_schema_extra={
            "name": "state",
            "label": "State",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. California",
            "mapTo": "state",
            "order": 11,
        },
    )
    country: str = Field(
        json_schema_extra={
            "name": "country",
            "label": "Country",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. US",
            "mapTo": "country",
            "order": 12,
        },
    )
    zipcode: str = Field(
        json_schema_extra={
            "name": "zipCode",
            "label": "Zip Code",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. 90001",
            "mapTo": "zipcode",
            "order": 13,
        },
    )
    coupon_code: str | None = Field(
        default=None,
        json_schema_extra={
            "name": "couponCode",
            "label": "Coupon Code",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. VER15",
            "mapTo": "coupon_code",
            "order": 14,
        },
    )
    emailSent: bool = Field(
        default=False,
        json_schema_extra={
            "name": "emailSent",
            "label": "Email Sent",
            "type": "checkbox-group",
            "className": "form-control",
            "toggle": False,
            "inline": False,
            "other": False,
            "mapTo": "emailSent",
            "order": 15,
        },
    )

    @field_validator("country")
    @classmethod
    def validate_country(cls: type["VeritableSchema"], country: str) -> str:
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
                VeritableSchema,
            )
        return country

    @model_validator(mode="before")
    @classmethod
    def set_url(cls: type["VeritableSchema"], values: dict) -> dict:
        """
        set url based on tenant name
        """
        tenant = values.get("tenant")
        settings = ProductEnum.get_product_settings(ProductEnum.veritable)
        if tenant:
            values["url"] = f"https://{tenant}.{settings.tenant_fqdn}"
        return values


class PractiflySchema(BaseFormSchema):
    organization: str | None = Field(
        default=None,
        json_schema_extra={
            "name": "organizationName",
            "label": "Organization Name",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. ZZZ Medical",
            "mapTo": "organization",
            "order": 4,
        },
    )
    emailSent: bool = Field(
        default=False,
        json_schema_extra={
            "name": "emailSent",
            "label": "Email Sent",
            "type": "checkbox-group",
            "className": "form-control",
            "toggle": False,
            "inline": False,
            "other": False,
            "mapTo": "emailSent",
            "order": 6,
        },
    )


class JeevesSchema(BaseFormSchema):
    organization: str | None = Field(
        default=None,
        json_schema_extra={
            "name": "organizationName",
            "label": "Organization Name",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. ZZZ Medical",
            "mapTo": "organization",
            "order": 4,
        },
    )
    emailSent: bool = Field(
        default=False,
        json_schema_extra={
            "name": "emailSent",
            "label": "Email Sent",
            "type": "checkbox-group",
            "className": "form-control",
            "toggle": False,
            "inline": False,
            "other": False,
            "mapTo": "emailSent",
            "order": 6,
        },
    )
    companyNameProvidersOrPayersOnly: str = Field(
        json_schema_extra={
            "name": "companyNameProvidersOrPayersOnly",
            "label": "Company Name",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. AETNA",
            "mapTo": "companyNameProvidersOrPayersOnly",
            "order": 7,
        },
    )
    whichEhrDoesYourCompanyUse: str = Field(
        json_schema_extra={
            "name": "whichEhrDoesYourCompanyUse",
            "label": "Which EHR does your company use?",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. Epic",
            "mapTo": "whichEhrDoesYourCompanyUse",
            "order": 8,
        },
    )
    is_deployment: bool = Field(
        default=False,
        json_schema_extra={
            "name": "isDeployment",
            "label": "Is Deployment",
            "type": "checkbox-group",
            "className": "form-control",
            "toggle": False,
            "inline": False,
            "other": False,
            "mapTo": "is_deployment",
            "order": 9,
        },
    )


class DexitSchema(BaseFormSchema):
    organization: str | None = Field(
        default=None,
        json_schema_extra={
            "name": "organizationName",
            "label": "Organization Name",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. Z Medical Center",
            "mapTo": "organization",
            "order": 4,
        },
    )


class HDPSchema(BaseFormSchema):
    organization: str | None = Field(
        default=None,
        json_schema_extra={
            "name": "organizationName",
            "label": "Organization Name",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. ZZZ Medical Center",
            "mapTo": "organization",
            "order": 4,
        },
    )
    emailSent: bool = Field(
        default=False,
        json_schema_extra={
            "name": "emailSent",
            "label": "Email Sent",
            "type": "checkbox-group",
            "className": "form-control",
            "toggle": False,
            "inline": False,
            "other": False,
            "mapTo": "emailSent",
            "order": 6,
        },
    )


class ZsegmentSchema(BaseFormSchema):
    organization: str | None = Field(
        default=None,
        json_schema_extra={
            "name": "organizationName",
            "label": "Organization Name",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. ZZZ Medical Center",
            "mapTo": "organization",
            "order": 4,
        },
    )
    emailSent: bool = Field(
        default=False,
        json_schema_extra={
            "name": "emailSent",
            "label": "Email Sent",
            "type": "checkbox-group",
            "className": "form-control",
            "toggle": False,
            "inline": False,
            "other": False,
            "mapTo": "emailSent",
            "order": 6,
        },
    )
    PlanName: str = Field(
        default="Free",
        json_schema_extra={
            "name": "planName",
            "label": "Plan Name",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. Pro",
            "mapTo": "PlanName",
            "order": 7,
        },
    )


class PenknifeSchema(BaseFormSchema):
    phoneNumber: PhoneNumber = Field(
        json_schema_extra={
            "name": "phoneNumber",
            "label": "Phone Number",
            "subtype": "number",
            "className": "form-control",
            "mapTo": "phoneNumber",
            "order": 5,
        },
    )
    companyDomain: str = Field(
        json_schema_extra={
            "name": "companyDomain",
            "label": "Company Domain",
            "subtype": "text",
            "className": "form-control",
            "mapTo": "companyDomain",
            "order": 6,
        },
    )
    tenantType: TenantType = Field(
        default=TenantType.staffing,
        json_schema_extra={
            "name": "tenantType",
            "label": "Tenant Type",
            "subtype": "select",
            "className": "form-control",
            "mapTo": "tenantType",
            "order": 7,
        },
    )
    emailProvider: EmailProvider = Field(
        default=EmailProvider.google,
        json_schema_extra={
            "name": "emailProvider",
            "label": "Email Provider",
            "subtype": "select",
            "className": "form-control",
            "mapTo": "emailProvider",
            "order": 8,
        },
    )


ProductSchemaDataType = TypeVar(
    "ProductSchemaDataType",
    VeritableSchema,
    PractiflySchema,
    JeevesSchema,
    DexitSchema,
    HDPSchema,
    ZsegmentSchema,
    PenknifeSchema,
)

PRODUCT_SCHEMA_MAP = {
    ProductEnum.veritable: VeritableSchema,
    ProductEnum.practifly: PractiflySchema,
    ProductEnum.jeeves: JeevesSchema,
    ProductEnum.dexit: DexitSchema,
    ProductEnum.hdp: HDPSchema,
    ProductEnum.zsegment: ZsegmentSchema,
    ProductEnum.penknife: PenknifeSchema,
}


class ProductFormSchema(BaseModel):
    product: ProductEnum
    form_data: ProductSchemaDataType

    def __init__(self: "ProductFormSchema", **data: Any) -> None:
        super().__init__(**data)
        if not data.get("product"):
            raise ValidationError(["product is required"], ProductFormSchema)
        product = ProductEnum(data.get("product"))
        if product not in PRODUCT_SCHEMA_MAP:
            raise ValidationError(["invalid product"], ProductFormSchema)
        self.form_data = PRODUCT_SCHEMA_MAP[product](**data.get("form_data"))
