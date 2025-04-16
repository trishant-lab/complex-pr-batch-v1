from better_profanity import profanity
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.billing_models import RESERVED_TENANT_NAMES
from app.models.input_param_patterns import TENANT_NAME_PATTERN


class BaseFormSchema(BaseModel):
    firstName: str = Field(
        json_schema_extra={
            "name": "firstName",
            "label": "First Name",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. John",
            "mapTo": "firstName",
            "order": 1,
        },
    )
    lastName: str = Field(
        json_schema_extra={
            "name": "lastName",
            "label": "Last Name",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. Doe",
            "mapTo": "lastName",
            "order": 2,
        },
    )
    email: EmailStr = Field(
        json_schema_extra={
            "name": "workEmail",
            "label": "Work Email",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. john.doe@example.com",
            "mapTo": "email",
            "order": 3,
        },
    )
    organization: str = Field(
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
    tenant: str = Field(
        pattern=TENANT_NAME_PATTERN,
        json_schema_extra={
            "name": "tenantName",
            "label": "Tenant Name",
            "subtype": "text",
            "className": "form-control",
            "placeholder": "e.g. test1",
            "mapTo": "tenant",
            "order": 5,
        },
    )

    @field_validator("tenant")
    @classmethod
    def validate_tenant(cls: type["BaseFormSchema"], tenant: str) -> str | None:
        """
        Validate tenant name
        """
        if tenant and tenant.lower() in RESERVED_TENANT_NAMES:
            raise ValueError("Invalid tenant/portal name!")

        if profanity.contains_profanity(tenant):
            raise ValueError("Explicit words are not allowed in tenant/portal name!")
        return tenant

    @classmethod
    def get_mapping_dict(cls) -> dict:
        """
        Get mapping dict
        """
        return {
            "required": [field_name for field_name, field in cls.model_fields.items() if field.is_required()],
            "optional": [field_name for field_name, field in cls.model_fields.items() if not field.is_required()],
        }
