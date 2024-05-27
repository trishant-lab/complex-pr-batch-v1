from fastapi import APIRouter, Depends
from ..cli.temporal.veritable.starter import trigger_veritable_de_provisioning_workflow
from ..core.oauth2 import get_oauth_scheme

de_provisioning_router = APIRouter()


de_provisioning_trigger_functions = {
    "veritable": trigger_veritable_de_provisioning_workflow,
    "jeeves": None
}


@de_provisioning_router.post(
    "",
    operation_id="deprovisionTenant",
    summary="Deprovision tenant",
)
async def de_provision_tenant(product: str, tenant: str, _: dict = Depends(get_oauth_scheme())):
    """
    Deprovision tenant
    """
    # Trigger deprovisioning workflow
    trigger_function = de_provisioning_trigger_functions[product]
    if trigger_function:
        await trigger_function(tenant)
    else:
        return {"message": "Invalid product"}

    return {"message": f"Deprovisioning workflow triggered successfully for {product} {tenant} tenant"}
