from datetime import datetime
from enum import Enum
from types import UnionType

from pydantic import BaseModel, EmailStr, ValidationError

from app.utils.s3_operations import get_s3_client
from app.core.ijson import ijson_dumps, ijson_loads
from app.core.settings import AppSettings, get_settings
from app.exceptions import errors
from app.form_render import form_render_for_product
from app.models.billing_models import PhoneNumber
from app.models.form_schema.product_schema import PRODUCT_SCHEMA_MAP, ProductSchemaDataType
from app.models.product import ProductEnum


class ProductResponseModel(BaseModel):
    name: ProductEnum
    formSchema: list[dict]
    created: datetime
    lastmodified: datetime
    approvalRequired: bool
    mapping: dict

    @classmethod
    def json_to_model(cls, data: dict) -> "ProductResponseModel":
        """
        Convert db response to model
        """
        data["formSchema"] = ijson_loads(data["schema"])
        data["lastmodified"] = data["lastupdated"]
        product = ProductEnum(data["name"])
        data["mapping"] = PRODUCT_SCHEMA_MAP[product].get_mapping_dict()
        return cls(**data)


async def upload_form_to_r2_bucket(product: ProductEnum) -> None:
    """
    @param product:
    @return:
    """
    config: AppSettings = get_settings()
    form: dict = await form_render_for_product(product.value)

    storage_client = get_s3_client(
        access_key=config.r2.access_key,
        secret_key=config.r2.secret_key,
        endpoint=config.r2.endpoint,
        bucket_name=config.r2.bucket,
    )
    form_path = f"{product.value}/form.json"

    await storage_client.upload_object(
        path=form_path,
        file_name="form.json",
        content_type="application/json",
        file_content=ijson_dumps(form).encode(),
    )


async def validate_provisioning_details(
    product: ProductEnum, data: dict, schema: list[dict] | None = None
) -> tuple[list[dict], ProductSchemaDataType]:
    """
    Validate provisioning details
    """
    from app.routes.provisioning import get_product

    if not schema:
        resp = await get_product(product=product)
        schema = resp.formSchema

    model_data = {}
    missing_required_fields = []
    for field in schema:
        field_name = field["name"]
        if data.get(field_name):
            if field.get("mapTo"):
                model_data[field["mapTo"]] = data.get(field_name)
        elif field["required"]:
            missing_required_fields.append(field_name)
    if missing_required_fields:
        raise errors.REQUIRED_FIELD_MISSING.exc(fields=missing_required_fields)

    try:
        product_schema = PRODUCT_SCHEMA_MAP[product]
        provisioning_model = product_schema.model_validate(model_data)
    except ValidationError as e:
        error_message = [error["msg"] for error in e.errors()]
        raise errors.INVALID_SCHEMA.exc(e=error_message)

    return schema, provisioning_model


# Map form field types to Pydantic types
TYPE_MAPPING = {
    "text": (str, EmailStr, PhoneNumber),
    "email": (str, EmailStr),
    "number": (int, float, PhoneNumber),
    "select": (str, Enum),
    "checkbox": (bool,),
    "textarea": (str,),
    "null": (None,),
}


def check_duplicate_mappings(product_schema: list[dict]) -> dict:
    """
    Create a dictionary of mapTo fields with their requirements
    """
    mapped_fields = {}
    for field in product_schema:
        field_name = field.get("name")
        mapping = field.get("mapTo")

        if mapping:
            # Check for duplicate mappings
            if mapping in mapped_fields:
                raise ValueError(
                    f"Duplicate mapping '{mapping}' found for fields: "
                    f"'{mapped_fields[mapping]['field_name']}' and '{field_name}'"
                )

            # Store field details in dictionary
            mapped_fields[mapping] = {
                "field_name": field_name,
                "required": field.get("required", False),
                "type": field.get("type", "").lower(),
            }
    return mapped_fields


def validate_product_schema(product: ProductEnum, product_schema: list[dict]) -> None:
    """
    Validate product schema using a dictionary-based approach
    """
    schema_class = PRODUCT_SCHEMA_MAP[product]
    model_fields = schema_class.model_fields
    mapped_fields = check_duplicate_mappings(product_schema)

    # Validate mapped fields against model fields
    for mapping, field_info in mapped_fields.items():
        # Validate mapping exists in model
        if mapping not in model_fields:
            raise ValueError(
                f"Field '{field_info['field_name']}' maps to '{mapping}' which doesn't exist "
                f"in {product.value} schema"
            )

        # Validate field type matches model
        model_field = model_fields[mapping]
        field_type = field_info["type"]

        if field_type not in TYPE_MAPPING:
            continue

        if model_field.is_required() and not field_info["required"]:
            raise ValueError(f"Field '{field_info['field_name']}' is required but the schema indicates it is not")

        annotation = (
            tuple(t for t in model_field.annotation.__args__)
            if type(model_field.annotation) is UnionType
            else (model_field.annotation,)
        )

        if not any(t in TYPE_MAPPING[field_type] for t in annotation):
            raise ValueError(
                f"Field '{field_info['field_name']}' type doesn't match schema type '{TYPE_MAPPING[field_type]}'"
            )


def validate_email_domain(product: ProductEnum, email: EmailStr) -> None:
    """
    Validate the email domain
    """
    settings = ProductEnum.get_product_settings(product)
    email_domain = email.split("@")[-1]
    if email_domain in (getattr(settings, "email_domains_exclusions", None) or []):
        raise errors.INVALID_EMAIL.exc(email=email)
