from fastapi import APIRouter
# from ..temporalworkflows.veritable.deprovisioning.deprovisioning_helper import trigger_veritable_deprovisioning_workflow

deprovisioning_router = APIRouter()


deprovisioning_trigger_functions = {
    "veritable": None,
    "jeeves": None
}


@deprovisioning_router.post(
    "/deprovision",
    operation_id="deprovisionTenant",
    summary="Deprovision tenant",
)
async def deprovision_tenant(product: str, tenant: str):
    """
    Deprovision tenant
    """
    # Trigger deprovisioning workflow
    trigger_function = deprovisioning_trigger_functions[product]
    if trigger_function:
        await trigger_function(tenant)
    else:
        return {"message": "Invalid product"}

    return {"message": f"Deprovisioning workflow triggered successfully for {product} {tenant} tenant"}
