from fastapi import APIRouter, Path
from lago_python_client.exceptions import LagoApiError
from starlette.status import HTTP_200_OK

from app.core.connections import get_lago_client
from app.exceptions import errors
from app.models.billing_models import PlanModel, PlanResponseModel
from app.models.product import ProductEnum
from app.route_utils.plans_util import get_plans_info

router = APIRouter()


@router.get(
    "/{product}",
    operation_id="getPlans",
    response_model=PlanResponseModel,
    summary="get all plans",
    status_code=HTTP_200_OK,
)
async def get_plans_(product: ProductEnum = Path(...)) -> PlanResponseModel:
    """
    :return:
    """
    try:
        plans = get_plans_info(product)
        plan_response_model = PlanResponseModel(monthly=[], yearly=[])
        lago_client = get_lago_client(product) if plans else None
        for plan in plans:
            plan_resp = lago_client.plans().find(plan["code"])
            plan_obj = {
                "features": plan["features"],
                "popular": plan["popular"],
                "addons": plan["addons"],
                "description": plan["description"],
                **plan_resp.dict(),
            }
            if plan["code"].__contains__("_m_"):
                plan_response_model.monthly.append(PlanModel.model_validate(plan_obj))
            if plan["code"].__contains__("_y_"):
                plan_response_model.yearly.append(PlanModel.model_validate(plan_obj))

        plan_response_model.monthly.sort(key=lambda x: x.amount_cents)
        plan_response_model.yearly.sort(key=lambda x: x.amount_cents)

        return plan_response_model
    except (LagoApiError, KeyError):
        raise errors.PLAN_RESOURCE_NOT_FOUND.exc()
