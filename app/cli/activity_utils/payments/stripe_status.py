import stripe

from app.core.ijson import ijson_dumps, ijson_loads
from app.models.product import ProductEnum

__LAST_PAYMENT_ERROR_KEYS__ = {"code", "decline_code", "doc_url", "message", "param", "type"}


def _read_decline_reason(_d: stripe.PaymentIntent) -> str:
    last_payment_error = ijson_loads(str(_d.last_payment_error))
    result = {key: last_payment_error[key] for key in __LAST_PAYMENT_ERROR_KEYS__ if key in last_payment_error}
    return ijson_dumps(result)


async def get_stripe_failure_status(stripe_customer_id: str, invoice_id: str, product: ProductEnum) -> str | None:
    """
    @param invoice_id:
    @return:
    """
    stripe_api_key = ProductEnum.get_stripe_secret_key(product)
    pi = await stripe.PaymentIntent.search_async(
        query=f'metadata["lago_invoice_id"]:"{invoice_id}"',
        api_key=stripe_api_key,
    )
    if pi.data:
        return _read_decline_reason(pi.data[0])

    pi = await stripe.PaymentIntent.list_async(customer=stripe_customer_id, api_key=stripe_api_key)
    if pi.data:
        for pi_data in pi.data:
            if pi_data.metadata["lago_invoice_id"] == invoice_id:
                return _read_decline_reason(pi_data)
    return None
