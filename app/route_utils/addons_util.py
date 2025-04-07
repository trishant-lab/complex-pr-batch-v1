from app.core.connections import get_lago_client
from app.core.db import DBManager
from app.models.billing_models import AddOnResponseModel
from app.models.enums import FeatureStatus
from app.models.lago.billable_metric import BillableMetricResponse
from app.models.lago.plan import PlanResponse
from app.models.product import ProductEnum

_ADDONS_CACHE = {}


def get_addon_name(product: ProductEnum, addon_metric_code: str) -> str:
    """
    @param addon_metric_code:
    @return: addon metric name from lago
    """
    lago_client = get_lago_client(product)
    lago_resp = lago_client.billable_metrics().find(addon_metric_code)
    resp = BillableMetricResponse.from_lago(lago_resp)
    return resp.name


def get_addon_price(product: ProductEnum, addon_metric_code: str, plan_code: str) -> float:
    """
    Retrieve the price for an addon metric code from a Lago plan.
    @param addon_metric_code: The metric code for the addon.
    @param plan_code: The code for the plan.
    @return: The price of the addon or 0 if not found.
    """
    lago_client = get_lago_client(product)
    plan_resp = lago_client.plans().find(plan_code)
    plan_response = PlanResponse.from_lago(plan_resp)

    # Find the charge matching the addon_metric_code
    charge = next(
        (charge for charge in plan_response.charges.root if charge.billable_metric_code == addon_metric_code), None
    )

    if not charge:
        return 0

    # Extract the graduated ranges for the current lago addon charge model
    graduated_ranges = charge.properties.get("graduated_ranges", [])

    # Find the price for the range where `from_value` is 0
    for prop in graduated_ranges:
        if prop.get("from_value") == 0:
            return float(prop.get("per_unit_amount", 0))

    return 0


async def get_plan_addons(plan_code: str, product: ProductEnum, db: DBManager) -> list[AddOnResponseModel]:
    """
    @param plan_code:
    @param db:
    @return: list of addons for a particular plan
    """
    param = {
        "plancode": plan_code,
        "status": FeatureStatus.active.value,
        "product": product.value,
    }
    records = await db.fetch_all("get_plan_add_ons.sql", **param)
    addons = [AddOnResponseModel.json_to_model(dict(record) | {"product": product}) for record in records]

    global _ADDONS_CACHE
    for addon in addons:
        if not _ADDONS_CACHE.get(product.value):
            _ADDONS_CACHE[product.value] = {}
        _ADDONS_CACHE[product.value][addon.code.value] = addon

    return addons


def get_all_addons(product: ProductEnum) -> list[AddOnResponseModel]:
    """
    @return: ALl addons details
    """
    if not _ADDONS_CACHE.get(product.value):
        return []
    return [addon for _, addon in _ADDONS_CACHE[product.value].items()]


def get_addons_from_features(product: ProductEnum, features: list) -> list:
    """
    @return: All addons feature code
    """
    all_addons = [code for code, _ in _ADDONS_CACHE[product.value].items()]
    addon_type = ProductEnum.get_add_on_enum(product)
    return [addon_type(feature) for feature in features if feature in all_addons]
