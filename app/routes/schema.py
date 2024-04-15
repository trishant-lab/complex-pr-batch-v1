from fastapi import APIRouter

schema_router = APIRouter()


@schema_router.get("")
async def get_schemas():
    return [
        {
            "id": "1",
            "name": "Schema 1",
            "description": "Schema 1 description",
        },
        {
            "id": "2",
            "name": "Schema 2",
            "description": "Schema 2 description",
        },
    ]