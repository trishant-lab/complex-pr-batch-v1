from typing import TYPE_CHECKING
from uuid import UUID

from loguru import logger
from pydantic import ValidationError

from app.cli.temporal.core.exceptions import NonRetryableException
from app.core.db import get_db_manager
from app.core.ijson import ijson_loads
from app.models.product import ProductEnum

if TYPE_CHECKING:
    from app.cli.base_workflow import ProductWorkflow


async def trigger_provisioning_workflow(customer_id: UUID, product: ProductEnum) -> None:
    """
    Create Veritable crd resource
    """
    db = await get_db_manager()
    resp = await db.fetch_one("get.sql", table="customer", where=f"id='{customer_id!s}'", columns=["data"])
    schema = ijson_loads(resp["data"])
    schema["customerId"] = customer_id

    try:
        product_model = ProductEnum.get_input_model_class(product)
        product_model.model_validate(schema)
    except ValidationError as e:
        logger.error(f"Invalid schema: {e.errors()}")
        raise NonRetryableException(f"Invalid schema: {e.errors()}")

    product_workflow: ProductWorkflow = ProductEnum.get_class(product)()
    await product_workflow.onboard(schema)
    logger.info(f"Triggered provisioning workflow for product: {product.value}")
