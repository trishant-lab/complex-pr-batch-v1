from app.models.billing_models import CustomerModel, CustomerPatchModel
from app.models.lago.customer import CustomerResponse, Metadata, MetadataList


def update_customer_model(
    instance: CustomerPatchModel | CustomerModel,
    updates: CustomerModel | CustomerPatchModel,
) -> dict:
    """
    Recursively parse models
    @param instance:
    @param updates:
    @return:
    """
    allowed_keys = {
        "name",
        "legal_name",
        "phone",
        "address_line1",
        "address_line2",
        "city",
        "country",
        "state",
        "zipcode",
        "url",
    }
    instance_data = instance.model_dump(exclude_unset=True, exclude_none=True)
    updated_data = updates.model_dump(exclude_unset=True, exclude_none=True, include=allowed_keys)
    return instance_data | updated_data


def update_customer_metadata(customer: CustomerModel | CustomerResponse, tenant_name: str | None) -> None:
    """
    @return:
    """
    if tenant_name:
        tenant_name_metadata = Metadata(key="tenant_name", value=tenant_name)
        if not customer.metadata or not customer.metadata.root:
            customer.metadata = MetadataList(root=[tenant_name_metadata])
        else:
            for metadata in customer.metadata.root:
                if metadata.key == "tenant_name":
                    metadata.value = tenant_name
                    break
