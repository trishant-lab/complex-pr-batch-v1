import orjson
from fastapi import APIRouter, Depends
from loguru import logger
from pydantic import ValidationError
from starlette.exceptions import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from app.cli.temporal.veritable.starter import trigger_veritable_onboarding_workflow
from app.cli.temporal.jeeves.starter import trigger_jeeves_onboarding_workflow
from ..core.db import DBManager, get_db_manager
from ..core.oauth2 import get_oauth_scheme
from ..core.settings import get_settings, AppSettings

from ..models.product_schema import VeritableSchema, JeevesSchema

onboarding_router = APIRouter()


onboarding_trigger_functions = {
    "veritable": trigger_veritable_onboarding_workflow,
    "jeeves": trigger_jeeves_onboarding_workflow,
}

product_schema = {
    "veritable": VeritableSchema,
    "jeeves": JeevesSchema
}


@onboarding_router.post("")
async def onboarding(product: str, schema: dict, _: dict = Depends(get_oauth_scheme())):
    """
    Trigger onboarding workflow for the given product
    """

    config: AppSettings = get_settings()
    # Validate schema
    try:
        validated_schema = product_schema[product].model_validate_json(orjson.dumps(schema).decode("utf-8"))
    except ValidationError as e:
        logger.error(f"Invalid schema: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid schema")

    # insert tenant into DB
    try:
        # parameters = {
        #     "tenant_name": validated_schema.tenant,
        #     "product": product,
        #     "status": "in-progress"
        # }
        # db: DBManager = await get_db_manager(config.postgres.dsn)
        # await db.fetch_one(
        #     "insertTenant.sql",
        #     db_schema_name=config.postgres.schema_name,
        #     **parameters
        # )
        pass

    except Exception as e:
        logger.error(f"Error while creating tenant {validated_schema.tenant}: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while creating tenant {validated_schema.tenant}"
        )

    # Trigger onboarding workflow
    trigger_function = onboarding_trigger_functions[product]
    if trigger_function:
        await trigger_function(validated_schema.dict())
    else:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid product")

    logger.info(f"Triggered onboarding workflow for product: {product}")

    return {"message": f"Onboarding workflow triggered successfully for product: {product}"}
