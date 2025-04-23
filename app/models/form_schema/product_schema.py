from typing import TypeVar

from pydantic import Field, ValidationError, field_validator, model_validator

from app.cli.temporal.penknife.models.penknife_spec import EmailProvider, TenantType
from app.models.billing_models import COUNTRY_CODES, PhoneNumber
from app.models.form_schema.base_schema import BaseFormSchema
from app.models.product import ProductEnum


class VeritableSchema(BaseFormSchema):
    phone: PhoneNumber | None = Field(
        default=None,
        json_schema_extra={
            "name": "phoneNumber",
            "label": "Phone Number",
            "subtype": "number",
            "className": "form-control",
            "placeholder": "e.g. 1234567890",
            "mapTo": "phone",
            "order": 6,
        },
    )
    address: str | None = Field(
        default=None,
        json_schema_extra={
            "name": "address",
            "label": "Address",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. 1234 Main St",
            "mapTo": "address",
            "order": 7,
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
            "order": 8,
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
            "order": 9,
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
            "order": 10,
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
            "order": 11,
        },
    )
    couponCode: str | None = Field(
        default=None,
        json_schema_extra={
            "name": "couponCode",
            "label": "Coupon Code",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. VER15",
            "mapTo": "couponCode",
            "order": 12,
        },
    )
    selectedApps: list[str] | None = Field(
        default=None,
        json_schema_extra={
            "name": "selectedApps",
            "label": "Selected Apps",
            "subtype": "multi_select",
            "hidden": True,
            "className": "form-control",
            "mapTo": "selectedApps",
            "order": 13,
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
    companyNameProvidersOrPayersOnly: str = Field(
        json_schema_extra={
            "name": "companyNameProvidersOrPayersOnly",
            "label": "Company Name",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. AETNA",
            "mapTo": "companyNameProvidersOrPayersOnly",
            "order": 6,
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
            "order": 7,
        },
    )
    customerDomain: str | None = Field(
        default=None,
        json_schema_extra={
            "name": "customerDomain",
            "label": "Customer Domain",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. zzzmedical.com",
            "mapTo": "customerDomain",
            "order": 8,
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
    planName: str = Field(
        default="Free",
        json_schema_extra={
            "name": "planName",
            "label": "Plan Name",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. Pro",
            "mapTo": "PlanName",
            "order": 6,
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
    tenantType: str = Field(
        default=TenantType.staffing.value,
        json_schema_extra={
            "name": "tenantType",
            "label": "Tenant Type",
            "subtype": "select",
            "options": [
                {"value": TenantType.staffing.value, "label": "Staffing"},
                {"value": TenantType.internalhiring.value, "label": "Internal Hiring"},
            ],
            "className": "form-control",
            "mapTo": "tenantType",
            "order": 7,
        },
    )
    emailProvider: str = Field(
        default=EmailProvider.google.value,
        json_schema_extra={
            "name": "emailProvider",
            "label": "Email Provider",
            "subtype": "select",
            "options": [
                {"value": EmailProvider.google.value, "label": "Google"},
                {"value": EmailProvider.microsoft.value, "label": "Microsoft"},
            ],
            "className": "form-control",
            "mapTo": "emailProvider",
            "order": 8,
        },
    )


class PricedxSchema(BaseFormSchema):
    isDeployment: bool = Field(
        default=False,
        json_schema_extra={
            "name": "isDeployment",
            "label": "Is Deployment",
            "type": "checkbox-group",
            "className": "form-control",
            "toggle": False,
            "inline": False,
            "other": False,
            "mapTo": "isDeployment",
            "order": 9,
        },
    )
    # Used for creating HPT Console Application for Pricedx
    isConsole: bool = Field(
        default=False,
        json_schema_extra={
            "name": "isConsole",
            "label": "Is Pricedx Console Application",
            "type": "checkbox-group",
            "className": "form-control",
            "toggle": False,
            "inline": False,
            "other": False,
            "mapTo": "isConsole",
            "order": 10,
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
            "order": 6,
        },
    )
    address: str | None = Field(
        default=None,
        json_schema_extra={
            "name": "address",
            "label": "Address",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. 1234 Main St",
            "mapTo": "address",
            "order": 7,
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
            "order": 8,
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
            "order": 9,
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
            "order": 10,
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
            "order": 11,
        },
    )
    couponCode: str | None = Field(
        default=None,
        json_schema_extra={
            "name": "couponCode",
            "label": "Coupon Code",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. VER15",
            "mapTo": "couponCode",
            "order": 12,
        },
    )
    organizationSize: str = Field(
        default="medium",
        json_schema_extra={
            "name": "organizationSize",
            "label": "Organization Size",
            "subtype": "select",
            "options": [
                {"value": "small", "label": "1-100 Beds"},
                {"value": "medium", "label": "101-500 Beds"},
                {"value": "large", "label": "501+ Beds"},
            ],
        },
    )
    numberOfProviders: str = Field(
        default="1-10",
        json_schema_extra={
            "name": "numberOfProviders",
            "label": "Number of Providers",
            "subtype": "select",
            "options": [
                {"value": "1-50", "label": "1-50 Providers"},
                {"value": "51-100", "label": "51-100 Providers"},
                {"value": "101-500", "label": "101-500 Providers"},
                {"value": "500+", "label": "500+ Providers"},
            ],
        },
    )
    reasonForUsingPricedx: str = Field(
        default="",
        json_schema_extra={
            "name": "reasonForUsingPricedx",
            "label": "Reason for using Pricedx",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. We are looking for a solution to manage our pricing and contracts",
            "mapTo": "reasonForUsingPricedx",
            "order": 13,
        },
    )
    emailSent: bool = Field(
        default=False,
        json_schema_extra={
            "name": "emailSent",
            "label": "Email Sent",
            "type": "checkbox-group",
            "className": "form-control",
            "toggle": True,
            "inline": False,
            "other": False,
            "mapTo": "emailSent",
            "hidden": True,
            "order": 14,
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
    def set_url(cls: type["PricedxSchema"], values: dict) -> dict:
        """
        set url based on tenant name
        """
        tenant = values.get("tenant")
        settings = ProductEnum.get_product_settings(ProductEnum.pricedx)
        if tenant:
            values["url"] = f"https://{tenant}.{settings.tenant_fqdn}"
        return values


class MuspellSchema(BaseFormSchema):
    organization: str | None = Field(
        default=None,
        json_schema_extra={
            "name": "organizationName",
            "label": "Organization Name",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. Z Medical",
            "mapTo": "organization",
            "order": 4,
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
    PricedxSchema,
    MuspellSchema,
)

PRODUCT_SCHEMA_MAP = {
    ProductEnum.veritable: VeritableSchema,
    ProductEnum.practifly: PractiflySchema,
    ProductEnum.jeeves: JeevesSchema,
    ProductEnum.dexit: DexitSchema,
    ProductEnum.hdp: HDPSchema,
    ProductEnum.zsegment: ZsegmentSchema,
    ProductEnum.penknife: PenknifeSchema,
    ProductEnum.pricedx: PricedxSchema,
    ProductEnum.muspell: MuspellSchema,
}
