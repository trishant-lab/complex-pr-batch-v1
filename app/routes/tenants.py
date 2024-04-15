from fastapi import APIRouter

tenants_router = APIRouter()


@tenants_router.get("")
async def get_tenants():
    return [
        {
            "id": "1",
            "name": "Tenant 1",
            "description": "Tenant 1 description",
        },
        {
            "id": "2",
            "name": "Tenant 2",
            "description": "Tenant 2 description",
        },
    ]