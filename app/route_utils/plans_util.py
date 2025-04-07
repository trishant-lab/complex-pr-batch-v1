from app.core.db import DBManager, get_db_manager
from app.core.ijson import ijson_loads
from app.exceptions import errors
from app.models.enums import MarketingType, PlanStatus
from app.models.product import ProductEnum
from app.route_utils.addons_util import get_plan_addons

_ACTIVE_PLAN_CODES: dict[str, list[str]] = {}
_PLANS_CACHE = {}


async def prefetch_plans() -> None:
    """
    @param product:
    @return:
    """
    db: DBManager = await get_db_manager()

    global _ACTIVE_PLAN_CODES
    global _PLANS_CACHE
    for product in ProductEnum:
        plans = await db.fetch_all("get_plans.sql", product=product.value)
        _PLANS_CACHE[product.value] = {}
        _ACTIVE_PLAN_CODES[product.value] = []
        for plan in plans:
            if plan["status"] == PlanStatus.active.value:
                _ACTIVE_PLAN_CODES[product.value].append(plan["plancode"])
            addons = await get_plan_addons(plan["plancode"], product, db)
            _PLANS_CACHE[product.value][plan["plancode"]] = {
                "code": plan["plancode"],
                "description": plan["description"],
                "features": ijson_loads(plan["features"]),
                "popular": MarketingType(plan["marketingtype"]) == MarketingType.popular,
                "addons": addons,
                "includedFeatures": ijson_loads(plan["includedFeatures"]),
            }


def get_plans_info(product: ProductEnum, codes: list[str] | None = None) -> list[dict]:
    """
    @param codes:
    @return:
    """
    if not codes:
        codes = _ACTIVE_PLAN_CODES[product.value]
    return [_PLANS_CACHE[product.value][code] for code in codes]


def verify_active_plan_codes(product: ProductEnum, code: str) -> None:
    """
    @param code:
    @return:
    """
    if code not in _ACTIVE_PLAN_CODES[product.value]:
        raise errors.PLAN_INACTIVE_ERROR.exc()


async def verify_enterprise_plans(product: ProductEnum, code: str) -> None:
    """
    @param code:
    @return:
    """
    db: DBManager = await get_db_manager()
    plan = await db.fetch_one("get_enterprise_plan.sql", code=code, product=product.value)
    if not plan or plan["status"] != PlanStatus.enterprise.value:
        raise errors.PLAN_INACTIVE_ERROR.exc()
