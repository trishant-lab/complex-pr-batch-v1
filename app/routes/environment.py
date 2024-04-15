from fastapi import APIRouter

environment_router = APIRouter()


@environment_router.get("")
async def get_environments():
    return [
        {
            "id": "1",
            "name": "Environment 1",
            "description": "Environment 1 description",
        },
        {
            "id": "2",
            "name": "Environment 2",
            "description": "Environment 2 description",
        },
    ]