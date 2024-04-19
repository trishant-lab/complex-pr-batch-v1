import orjson
from fastapi import APIRouter
from loguru import logger
from pydantic import ValidationError
from starlette.exceptions import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST

from app.temporalworkflows.veritable.onboarding.onboardinghelper import trigger_veritable_onboarding_workflow

from ..models.product_schema import VeritableSchema

onboarding_router = APIRouter()


onboarding_trigger_functions = {
    "veritable": trigger_veritable_onboarding_workflow,
    "jeeves": None
}

product_schema = {
    "veritable": VeritableSchema,
}


@onboarding_router.post("")
async def onboarding(product: str, schema: dict):
    """
    Trigger onboarding workflow for the given product
    """

    # Validate schema
    try:
        validated_schema = product_schema[product].model_validate_json(orjson.dumps(schema).decode("utf-8"))
    except ValidationError as e:
        logger.error(f"Invalid schema: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid schema")

    # Trigger onboarding workflow
    trigger_function = onboarding_trigger_functions[product]
    if trigger_function:
        await trigger_function(validated_schema.dict())
    else:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid product")

    logger.info(f"Triggered onboarding workflow for product: {product}")

    return {"message": f"Onboarding workflow triggered successfully for product: {product}"}
