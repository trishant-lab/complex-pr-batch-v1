from app.core.connections import get_lago_client
from app.models.lago.subscription import SubscriptionResponse
from app.models.product import ProductEnum


def is_enterprise_plan(data: dict) -> bool:
    """
    :param data: event data
    :return: bool: belongs to enterprise plan
    """
    event_data = data.get(data.get("object_type"))
    customer_id = event_data.get("external_customer_id") or event_data.get("customer", {}).get("external_id")
    product = ProductEnum(data.get("product"))
    lago_client = get_lago_client(product)
    data = lago_client.subscriptions().find_all({"external_customer_id": customer_id})
    subs = [SubscriptionResponse.from_lago(sub) for sub in data.get("subscriptions")]
    if any(item.plan_code.startswith("ee_") for item in subs):
        return True
    return False
