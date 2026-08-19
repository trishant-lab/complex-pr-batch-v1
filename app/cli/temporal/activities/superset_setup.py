from datetime import timedelta

import aiohttp
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_info, log_error

REQUIRED_ROLES = ["TenantUser"]


class SupersetTenantSetupActivityModel(LaunchpadCLIBaseModel):
    """Input model for SupersetTenantSetupActivity"""

    tenant: str
    first_name: str
    last_name: str
    email: str
    superset_base_url: str
    superset_admin_username: str
    superset_admin_password: str
    tenant_password: str
    product_group: str


class SupersetTenantSetupActivity(Activity):
    """
    Provisions a dedicated Superset user for a tenant during onboarding.

    The tenant user is created with:
    - TenantUser role: linked to RLS rules for both embedded dashboards and reports
    - Product group (e.g. Dexit): for organisational grouping

    Idempotent: if the user already exists, verifies that the required roles
    and group are assigned and fixes them if not.
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """Timeout for the activity."""
        return timedelta(seconds=60)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """RetryPolicy for the activity."""
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="SupersetTenantSetupActivity")
    async def defn(activity_model: SupersetTenantSetupActivityModel) -> None:
        """Provision a Superset tenant user with required roles and group."""
        base_url = activity_model.superset_base_url
        tenant = activity_model.tenant
        product_group = activity_model.product_group

        if not base_url:
            log_info("Superset base URL not configured — skipping tenant user provisioning")
            return

        async with aiohttp.ClientSession() as session:
            # Login as admin
            async with session.post(
                f"{base_url}/api/v1/security/login",
                json={
                    "username": activity_model.superset_admin_username,
                    "password": activity_model.superset_admin_password,
                    "provider": "db",
                },
            ) as login_resp:
                if login_resp.status != 200:
                    body = await login_resp.text()
                    log_error(f"Superset admin login failed: status={login_resp.status} body={body}")
                    raise RuntimeError(f"Superset admin login failed: {login_resp.status}")

                access_token = (await login_resp.json()).get("access_token", "")

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # Resolve required role IDs
            required_role_ids = await _resolve_role_ids(session, base_url, headers, REQUIRED_ROLES)

            # Resolve product group ID
            group_id = await _resolve_group_id(session, base_url, headers, product_group)

            # Fetch CSRF token for write operations
            csrf_token = ""
            async with session.get(f"{base_url}/api/v1/security/csrf_token/", headers=headers) as csrf_resp:
                if csrf_resp.status == 200:
                    csrf_token = (await csrf_resp.json()).get("result", "")

            write_headers = {
                **headers,
                "X-CSRFToken": csrf_token,
                "Referer": base_url,
            }

            # Check if tenant user already exists
            rison_filter = f"(filters:!((col:username,opr:eq,value:'{tenant}')))"
            users = []
            async with session.get(
                f"{base_url}/api/v1/security/users/",
                headers=headers,
                params={"q": rison_filter},
            ) as users_resp:
                if users_resp.status == 200:
                    users = (await users_resp.json()).get("result", [])

            if users:
                user = users[0]
                user_id = user["id"]
                log_info(
                    f"Superset user '{tenant}' already exists (id={user_id}) — "
                    f"refreshing password and verifying roles and group"
                )
                await _ensure_user_state(
                    session,
                    base_url,
                    write_headers,
                    user_id,
                    user,
                    required_role_ids,
                    group_id,
                    tenant,
                    product_group,
                    tenant_password=activity_model.tenant_password,
                )
                return

            # Create the tenant user
            async with session.post(
                f"{base_url}/api/v1/security/users/",
                json={
                    "username": tenant,
                    "password": activity_model.tenant_password,
                    "first_name": activity_model.first_name,
                    "last_name": activity_model.last_name,
                    "email": activity_model.email,
                    "active": True,
                    "roles": list(required_role_ids.values()),
                },
                headers=write_headers,
            ) as create_resp:
                if create_resp.status not in (200, 201):
                    body = await create_resp.text()
                    log_error(f"Failed to create Superset user '{tenant}': status={create_resp.status} body={body}")
                    raise RuntimeError(f"Superset user creation failed: {create_resp.status}")

                data = await create_resp.json()

            user_id = data.get("id", "unknown")
            log_info(f"Superset user '{tenant}' created (id={user_id}) with roles {REQUIRED_ROLES}")

            # Assign group
            if group_id:
                await _add_user_to_group(session, base_url, write_headers, group_id, user_id, tenant, product_group)


async def _resolve_role_ids(
    session: aiohttp.ClientSession,
    base_url: str,
    headers: dict,
    role_names: list[str],
) -> dict[str, int]:
    """Fetch role IDs for each required role name. Raises if any role is missing."""
    result = {}
    for role_name in role_names:
        rison = f"(filters:!((col:name,opr:eq,value:'{role_name}')))"
        async with session.get(f"{base_url}/api/v1/security/roles/", headers=headers, params={"q": rison}) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(f"Failed to fetch role '{role_name}': status={resp.status} body={body}")

            roles = (await resp.json()).get("result", [])
        if not roles:
            raise RuntimeError(f"Role '{role_name}' not found in Superset")
        result[role_name] = roles[0]["id"]

    log_info(f"Resolved role IDs: {result}")
    return result


async def _resolve_group_id(
    session: aiohttp.ClientSession,
    base_url: str,
    headers: dict,
    group_name: str,
) -> int | None:
    """Fetch the group ID by name. Returns None if group doesn't exist (non-fatal)."""
    rison = f"(filters:!((col:name,opr:eq,value:'{group_name}')))"
    async with session.get(f"{base_url}/api/v1/security/groups/", headers=headers, params={"q": rison}) as resp:
        if resp.status != 200:
            log_info(f"Groups API returned {resp.status} — group assignment will be skipped")
            return None

        groups = (await resp.json()).get("result", [])
    if not groups:
        log_info(f"Group '{group_name}' not found in Superset — group assignment will be skipped")
        return None

    group_id = groups[0]["id"]
    log_info(f"Resolved group '{group_name}' -> id={group_id}")
    return group_id


async def _ensure_user_state(
    session: aiohttp.ClientSession,
    base_url: str,
    write_headers: dict,
    user_id: int,
    user: dict,
    required_role_ids: dict[str, int],
    group_id: int | None,
    tenant: str,
    group_name: str,
    tenant_password: str,
) -> None:
    """For an existing user, refresh password and ensure all required roles + group are assigned.

    Password is always re-PUT so the freshly-generated value (which is what gets
    written to 1Password by the caller) stays in sync with what Superset stores.
    Superset/FAB has no password-reuse policy, so resubmitting the same password
    is safe and effectively a no-op.
    """
    existing_role_ids = {r["id"] for r in user.get("roles", [])}
    merged_role_ids = list(existing_role_ids | set(required_role_ids.values()))

    async with session.put(
        f"{base_url}/api/v1/security/users/{user_id}",
        json={
            "password": tenant_password,
            "roles": merged_role_ids,
        },
        headers=write_headers,
    ) as update_resp:
        if update_resp.status == 200:
            added = set(required_role_ids.values()) - existing_role_ids
            if added:
                log_info(f"Refreshed password and added missing roles for user '{tenant}' (id={user_id})")
            else:
                log_info(f"Refreshed password for user '{tenant}' (id={user_id}); roles already correct")
        else:
            body = await update_resp.text()
            log_error(f"Failed to update user '{tenant}': status={update_resp.status} body={body}")
            raise RuntimeError(f"Failed to update Superset user: {update_resp.status}")  # nosec B608

    if group_id:
        await _add_user_to_group(session, base_url, write_headers, group_id, user_id, tenant, group_name)


async def _add_user_to_group(
    session: aiohttp.ClientSession,
    base_url: str,
    write_headers: dict,
    group_id: int,
    user_id: int,
    tenant: str,
    group_name: str,
) -> None:
    """Add user to the product group if not already a member.

    The FAB groups API uses PUT with the full users list — there's no
    sub-endpoint for adding individual users. So we GET the current
    members, append our user, and PUT the merged list back.
    """
    # Fetch current group to get existing user IDs
    async with session.get(
        f"{base_url}/api/v1/security/groups/{group_id}",
        headers=write_headers,
    ) as group_resp:
        if group_resp.status != 200:
            body = await group_resp.text()
            log_error(f"Failed to fetch group '{group_name}': status={group_resp.status} body={body}")
            return

        group_data = (await group_resp.json()).get("result", {})

    existing_user_ids = [u["id"] for u in group_data.get("users", [])]

    if user_id in existing_user_ids:
        log_info(f"User '{tenant}' already in group '{group_name}'")
        return

    # PUT the merged users list back to the group
    merged_user_ids = [*existing_user_ids, user_id]
    async with session.put(
        f"{base_url}/api/v1/security/groups/{group_id}",
        json={"users": merged_user_ids},
        headers=write_headers,
    ) as put_resp:
        if put_resp.status == 200:
            log_info(f"Added user '{tenant}' to group '{group_name}'")
        else:
            body = await put_resp.text()
            log_error(f"Failed to add user '{tenant}' to group '{group_name}': status={put_resp.status} body={body}")
