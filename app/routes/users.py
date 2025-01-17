import time
import uuid
from functools import lru_cache
from uuid import UUID

import aiohttp
import jwt
import orjson
from fastapi import APIRouter, Depends
from keycloak import urls_patterns
from loguru import logger
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.status import HTTP_204_NO_CONTENT, HTTP_500_INTERNAL_SERVER_ERROR

from app.cli.keycloakUtils import KeycloakAdminClient
from app.core.oauth2 import get_oauth_scheme
from app.core.settings import AppSettings, get_settings
from app.models.users import (
    RoleResponseModel,
    UserResponseModel,
    CreateUserRequestModel,
    UpdateUserRequestModel,
    GSuiteUser,
)

user_router = APIRouter()


def get_roles(kc_agent: KeycloakAdminClient, user_id: UUID, config: AppSettings) -> list[RoleResponseModel]:
    """
    get roles of a user
    """
    url = urls_patterns.URL_ADMIN_USER_REALM_ROLES_COMPOSITE.format(
        **{"realm-name": config.keycloak.realm, "id": user_id},
    )
    assigned_roles = kc_agent.kc_client.connection.raw_get(url)

    return [
        RoleResponseModel.json_to_model(role)
        for role in assigned_roles.json()
        if role["name"] not in ["default-roles-launchpad", "uma_authorization", "offline_access"]
    ]


@user_router.get(
    "",
    response_model=list[UserResponseModel] | None,
    operation_id="getUsers",
    summary="Returns all users in the keycloak realm",
)
async def get_keycloak_users(
    user_id: None | str = None, _: dict = Depends(get_oauth_scheme())
) -> list[UserResponseModel]:
    """
    Returns all users in the keycloak realm
    :return:
    """
    if user_id:
        return [await get_user_by_id(user_id=user_id)]

    config: AppSettings = get_settings()

    keycloak_admin_client = KeycloakAdminClient(config=config.keycloak)

    users = keycloak_admin_client.get_users(realm_name=config.keycloak.realm)

    users = [user for user in users if user.get("username") != "admin"]

    return [
        UserResponseModel.json_to_model(
            {"roles": get_roles(kc_agent=keycloak_admin_client, user_id=user["id"], config=config), **user}
        )
        for user in users
    ]


@user_router.get(
    "/getUserById",
    response_model=UserResponseModel,
    operation_id="getUserById",
    summary="Returns user by id",
)
async def get_user_by_id(user_id: str, _: dict = Depends(get_oauth_scheme())) -> UserResponseModel:
    """
    Returns user by id
    :param user_id:
    :param _: dict:
    :return:
    """
    config: AppSettings = get_settings()

    keycloak_admin_client = KeycloakAdminClient(config=config.keycloak)

    user = keycloak_admin_client.get_user(user_id=user_id, realm_name=config.keycloak.realm)

    return UserResponseModel.json_to_model(
        {"roles": get_roles(kc_agent=keycloak_admin_client, user_id=user["id"], config=config), **user}
    )


def fetch_assignable_roles(keycloak_admin_client: KeycloakAdminClient, config: AppSettings) -> list:
    """
    fetch assignable roles for the user
    """
    return [
        RoleResponseModel(**role)
        for role in keycloak_admin_client.get_realm_roles(realm_name=config.keycloak.realm)
        if role["name"] not in ["default-roles-launchpad", "uma_authorization", "offline_access"]
    ]


def get_request_scope_user(request: Request) -> dict:
    """
    Get the user from the request scope.
    """
    return request.scope.get("user") or {}


@user_router.get(
    "/roles",
    operation_id="getAssignableRoles",
    summary="returns assignable the roles",
    response_model=list,
)
def get_assignable_roles(
    _: dict = Depends(get_oauth_scheme()),
) -> list[RoleResponseModel]:
    """
    ## Fetches assignable roles to the user
    """
    config: AppSettings = get_settings()

    keycloak_admin_client = KeycloakAdminClient(config=config.keycloak)

    return fetch_assignable_roles(keycloak_admin_client=keycloak_admin_client, config=config)


def get_roles_data(kc_agent: KeycloakAdminClient, config: AppSettings, roles_data: list[RoleResponseModel]) -> list:
    """
    function to get the complete data for given roles
    """
    role_ids = {str(x.id) for x in roles_data}
    return [role for role in kc_agent.get_realm_roles(realm_name=config.keycloak.realm) if role["id"] in role_ids]


def update_roles(
    user_id: UUID,
    config: AppSettings,
    kc_agent: KeycloakAdminClient,
    added_roles: list[RoleResponseModel] | None,
    deleted_roles: list[RoleResponseModel] | None,
) -> None:
    """
    function to update roles for a user
    """
    url = urls_patterns.URL_ADMIN_USER_REALM_ROLES.format(
        **{"realm-name": config.keycloak.realm, "id": user_id},
    )

    deleted_roles = (
        (get_roles_data(kc_agent=kc_agent, config=config, roles_data=deleted_roles)) if deleted_roles else None
    )
    added_roles = (get_roles_data(kc_agent=kc_agent, config=config, roles_data=added_roles)) if added_roles else None

    if deleted_roles:
        response = kc_agent.kc_client.connection.raw_delete(url, data=orjson.dumps(deleted_roles))
        if response.status_code != HTTP_204_NO_CONTENT:
            logger.error("Error while Updating Role")
            raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error while Updating Role")
    if added_roles:
        response = kc_agent.kc_client.connection.raw_post(url, data=orjson.dumps(added_roles))
        if response.status_code != HTTP_204_NO_CONTENT:
            logger.error("Error while Adding Role")
            raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error while Adding Role")


@user_router.post(
    "",
    operation_id="createUser",
    summary="Creates a new user",
)
async def post_user(
    user: CreateUserRequestModel,
    _: dict = Depends(get_oauth_scheme()),
) -> None:
    """
    ## Creates user
    """
    kc_agent: KeycloakAdminClient = KeycloakAdminClient(config=get_settings().keycloak)
    kc_agent.refresh_token()

    config: AppSettings = get_settings()
    payload: dict = {
        "username": user.username,
        "email": user.email.lower(),
        "firstName": user.first_name,
        "lastName": user.last_name,
        "enabled": user.status,
        "emailVerified": True,
    }

    user_id: str = kc_agent.create_user(user_config=payload, realm_name=config.keycloak.realm)

    update_roles(user_id=UUID(user_id), added_roles=user.roles, deleted_roles=None, config=config, kc_agent=kc_agent)


@user_router.put(
    "",
    operation_id="updateUser",
    summary="Updates a user",
)
async def update_user(
    user: UpdateUserRequestModel,
    _: dict = Depends(get_oauth_scheme()),
) -> None:
    """
    ## Updates user
    """
    kc_agent: KeycloakAdminClient = KeycloakAdminClient(config=get_settings().keycloak)
    kc_agent.refresh_token()

    config: AppSettings = get_settings()
    payload: dict = {
        "email": user.email.lower() if user.email else None,
        "firstName": user.first_name if user.first_name else None,
        "lastName": user.last_name if user.last_name else None,
        "enabled": user.status,
    }

    kc_agent.kc_client.realm_name = config.keycloak.realm
    kc_agent.kc_client.update_user(user_id=user.user_id, payload=payload)
    update_roles(
        user_id=uuid.UUID(user.user_id),
        added_roles=user.added_roles,
        deleted_roles=user.deleted_roles,
        config=config,
        kc_agent=kc_agent,
    )


@lru_cache
async def get_g_suite_token(
    scope: str = "https://www.googleapis.com/auth/admin.directory.user",
) -> str:
    """

    :param scope: OAuth Scope
    :return:
    """
    config: AppSettings = get_settings()
    subject: str = config.gsuite.gsuite_admin
    private_key = config.gsuite.private_key.get_secret_value()
    token_uri = config.gsuite.token_uri

    now = int(time.time())
    jwt_payload = {
        "iss": config.gsuite.client_email,
        "sub": subject,
        "aud": config.gsuite.token_uri,
        "iat": now,
        "exp": now + 3600,  # Token expires in 1 hour
        "scope": scope,
    }

    jwt_headers = {"alg": "RS256", "kid": config.gsuite.private_key_id.get_secret_value()}
    signed_jwt = jwt.encode(jwt_payload, private_key, algorithm="RS256", headers=jwt_headers)

    async with aiohttp.ClientSession() as session:
        response = await session.post(
            token_uri, data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": signed_jwt}
        )
        if response.status == 200:
            data = await response.json()
            return data.get("access_token")
        else:
            raise aiohttp.ClientResponseError(f"Failed to get access token: {await response.text()}")


@user_router.get(
    "/getGSuiteUsersList",
    response_model=list[GSuiteUser],
    summary="retrieves a list of all GSuite Users",
    description="Gets a list of all GSuite Users which includes userID, emails, and name",
    operation_id="getGSuiteUsersList",
)
async def get_g_suite_users_list(_: dict = Depends(get_oauth_scheme())) -> list:
    """

    :return:  List of all GSuite Users
    """
    config: AppSettings = get_settings()
    token = await get_g_suite_token()
    users_list: list = []
    next_page_token: str = ""
    while True:
        parameters: dict = {"customer": config.gsuite.customer_id, "pageToken": next_page_token}

        async with aiohttp.ClientSession() as session:
            res = await session.get(
                "https://www.googleapis.com/admin/directory/v1/users",
                params=parameters,
                headers={"Authorization": f"Bearer {token}"},
            )
            if res.status != 200:
                raise HTTPException(status_code=400, detail="GSuite API Error")
            else:
                result: dict = await res.json()
                users_list.extend(result["users"]) if "users" in result.keys() else None
                if result.get("nextPageToken", ""):
                    next_page_token = result.get("nextPageToken")
                else:
                    break
    # extracting only id, email and name of each GSuite User
    return [
        {key: user.get(key) for key in ["id", "primaryEmail", "name", "aliases"]}
        for user in users_list
        if "314e" in user["primaryEmail"]
    ]


@user_router.delete(
    "",
    operation_id="deleteUser",
    summary="Deletes a user",
)
async def delete_user(
    user_id: str,
    _: dict = Depends(get_oauth_scheme()),
) -> None:
    """
    ## Deletes user
    """
    config: AppSettings = get_settings()
    kc_agent: KeycloakAdminClient = KeycloakAdminClient(config=config.keycloak)
    kc_agent.refresh_token()

    kc_agent.kc_client.connection.realm_name = config.keycloak.realm
    kc_agent.kc_client.delete_user(user_id=user_id)
