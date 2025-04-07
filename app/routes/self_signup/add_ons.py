from fastapi import APIRouter, Path
from starlette.status import HTTP_200_OK

from app.models.billing_models import AddOnResponseModel
from app.models.product import ProductEnum

router = APIRouter()


@router.get(
    "/{product}",
    operation_id="getAddOns",
    response_model=list[AddOnResponseModel],
    summary="get all add-ons",
    status_code=HTTP_200_OK,
)
def get_add_ons(product: ProductEnum = Path(...)) -> list[AddOnResponseModel]:
    """
    :return: list of add-ons
    """
    from app.route_utils.addons_util import get_all_addons

    return get_all_addons(product)
