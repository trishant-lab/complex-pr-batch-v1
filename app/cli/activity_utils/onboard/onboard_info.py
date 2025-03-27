import uuid

from app.cli.temporal.models.onboard import OnboardInfo
from app.core.db import DBManager, get_db_manager
from app.core.ijson import ijson_loads
from app.models.tenant import TenantStatusEnum


async def get_customer_onboard_info(customer_id: uuid.UUID) -> OnboardInfo:
    """
    Return Customer info from DB
    """
    db: DBManager = await get_db_manager()

    _subscription_params = dict(
        table="subscription s",
        where=f"s.customerid='{customer_id!s}'",
        columns=["s.id", "s.plancode", "s.created"],
    )

    _operator_status_params = dict(
        table="provisioningstatus p",
        where=f"p.customerid='{customer_id!s}'",
        columns=["p.status"],
    )

    _customer_params = dict(
        table="customer c",
        where=f"c.id='{customer_id!s}'",
        columns=["c.id", "c.tenantname"],
    )

    _existing_invoice_params = dict(
        table="failedinvoices",
        where=f"customerid='{customer_id!s}'",
    )

    _subscription, _operator_status, _customer, _existing_invoice = await db.fetch_many(
        [
            ("get.sql", _subscription_params),  # NOSONAR
            ("get.sql", _operator_status_params),
            ("get.sql", _customer_params),
            ("get.sql", _existing_invoice_params),
        ],
    )

    if not _customer:
        from app.exceptions import errors

        raise errors.CUSTOMER_NOT_FOUND.exc()

    _subscription = _subscription[0]
    _operator_status = _operator_status[0]
    _customer = _customer[0]
    failed_invoice_id: str | None = None
    failed_invoice_reason: dict | None = None
    if _existing_invoice:
        _existing_invoice = _existing_invoice[0]
        failed_invoice_id = str(_existing_invoice["invoiceid"])
        if _existing_invoice["reason"]:
            failed_invoice_reason = ijson_loads(_existing_invoice["reason"])

    return OnboardInfo(
        customer_id=customer_id,
        tenant_name=_customer["tenantname"],
        subscription_id=uuid.UUID(_subscription["id"]),
        subscription_plan=_subscription["plancode"],
        subscription_created=_subscription["created"],
        onboard_status=TenantStatusEnum(_operator_status["status"]),
        failed_invoice_id=failed_invoice_id,
        failed_invoice_reason=failed_invoice_reason,
    )


async def get_operator_status(customer_id: uuid.UUID) -> TenantStatusEnum:
    """
    Returns onboarding status
    """
    db: DBManager = await get_db_manager()
    _operator_status = await db.fetch_one(
        "get.sql",
        table="provisioningstatus p",
        where=f"p.customerid='{customer_id!s}'",
        columns=["p.status"],
    )
    return TenantStatusEnum(_operator_status["status"])


async def update_operator_status(
    customer_id: uuid.UUID,
    status: TenantStatusEnum,
    e: Exception,
    db: DBManager | None = None,
) -> None:
    """
    Update Provisioning status
    """
    db = db or await get_db_manager()

    payload = {"status": status, "errors": e.__str__()}
    await db.fetch_one(
        "put.sql",
        table="provisioningstatus",
        where=f"customerid='{customer_id!s}'",
        payload=payload,
    )
