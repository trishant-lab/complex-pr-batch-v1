import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

import aiohttp
from novu.api import IntegrationApi
from novu.dto import IntegrationDto
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity
from app.cli.temporal.core.log import log_info
from app.cli.temporal.dexit import TemplatePath
from app.cli.temporal.dexit.dexit import DexitSpec
from app.core.ijson import ijson_loads
from app.core.settings import AppSettings, get_settings
from app.one_password_util import OnePasswordUtil
from app.template_env import get_env


HEADER_CONTENT_TYPE = "application/json"

# Workflows are managed through the v2 API. A workflow created through POST /v1/workflows is
# listed by the current dashboard but cannot be opened there -- it reports origin
# "novu-cloud-v1", a placeholder step name and empty control values.
WORKFLOW_API_PATH = "/v2/workflows"
WORKFLOW_PAGE_SIZE = 100

# Creating a workflow is usually well under a second, but this endpoint spikes: 40s and 47s
# observed on an otherwise idle instance, and the first create after a quiet period is the
# usual victim. 60s was tight enough to abort a provisioning run mid-way.
WORKFLOW_TIMEOUT_SECONDS = 180

# Origin of a workflow the dashboard owns. Anything else was created through v1.
NOVU_CLOUD_ORIGIN = "novu-cloud"

# The v2 update body rejects these two create-only keys and requires an origin instead.
UPDATE_EXCLUDED_KEYS = ("workflowId", "__source")

# The only environment Dexit provisions. An api key belongs to exactly one environment and is
# what selects it, so nothing here reaches Development -- tenants run entirely on Production.
PRODUCTION_ENVIRONMENT = "Production"

# Throwaway subscriber used only to open an Inbox session; it owns no notifications.
INBOX_CONNECT_SUBSCRIBER_ID = "launchpad-inbox-connect"


@asynccontextmanager
async def _http(session: aiohttp.ClientSession | None) -> AsyncIterator[aiohttp.ClientSession]:
    """Reuse the caller's session, or open a short-lived one.

    Provisioning issues around thirty requests, and a fresh session per request costs a TLS
    handshake each time -- measured at roughly 800ms against Novu versus 300ms on a warm
    connection. Callers that make more than one request should pass their own.
    """
    if session is not None:
        yield session
    else:
        async with aiohttp.ClientSession() as owned:
            yield owned


async def _workflow_request(
    method: str,
    url: str,
    api_key: str,
    payload: dict | None = None,
    session: aiohttp.ClientSession | None = None,
) -> tuple[int, dict]:
    """Call the Novu workflow API with the environment key and return status plus body."""
    headers = {"Authorization": f"ApiKey {api_key}", "Content-Type": HEADER_CONTENT_TYPE}
    async with _http(session) as http:
        async with http.request(
            method,
            url,
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=WORKFLOW_TIMEOUT_SECONDS),
        ) as response:
            body = await response.json(content_type=None) if response.status != 204 else {}
            return response.status, body if isinstance(body, dict) else {}


async def list_novu_workflows(
    config: AppSettings, api_key: str, session: aiohttp.ClientSession | None = None
) -> list[dict]:
    """List every workflow in the environment the api key belongs to."""
    workflows: list[dict] = []
    page = 0
    while True:
        url = (
            f"{config.dexit.novu_url}{WORKFLOW_API_PATH}?limit={WORKFLOW_PAGE_SIZE}&offset={page * WORKFLOW_PAGE_SIZE}"
        )
        status, body = await _workflow_request("GET", url, api_key, session=session)
        if status >= 400:
            raise RuntimeError(f"Failed to list novu workflows: {body}")
        data = body.get("data", body)
        batch = data.get("workflows", []) if isinstance(data, dict) else data
        batch = [row for row in batch or [] if isinstance(row, dict)]
        workflows.extend(batch)
        if len(batch) < WORKFLOW_PAGE_SIZE:
            return workflows
        page += 1


async def create_novu_workflow(
    payload: dict, config: AppSettings, api_key: str, session: aiohttp.ClientSession | None = None
) -> None:
    """Create one workflow through the v2 API, so the dashboard can edit it."""
    url = f"{config.dexit.novu_url}{WORKFLOW_API_PATH}"
    status, body = await _workflow_request("POST", url, api_key, payload=payload, session=session)
    if status >= 400:
        raise RuntimeError(f"Failed to create novu workflow {payload.get('workflowId')}: {body}")


async def replace_novu_workflow(
    workflow_id: str, payload: dict, config: AppSettings, api_key: str, session: aiohttp.ClientSession | None = None
) -> None:
    """Replace a workflow the dashboard already owns, keeping its id and subscriber preferences."""
    update = {key: value for key, value in payload.items() if key not in UPDATE_EXCLUDED_KEYS}
    update["origin"] = NOVU_CLOUD_ORIGIN
    url = f"{config.dexit.novu_url}{WORKFLOW_API_PATH}/{workflow_id}"
    status, body = await _workflow_request("PUT", url, api_key, payload=update, session=session)
    if status >= 400:
        raise RuntimeError(f"Failed to update novu workflow {workflow_id}: {body}")


async def delete_novu_workflow(
    workflow_id: str, config: AppSettings, api_key: str, session: aiohttp.ClientSession | None = None
) -> None:
    """Delete one workflow. A missing workflow is treated as already deleted."""
    url = f"{config.dexit.novu_url}{WORKFLOW_API_PATH}/{workflow_id}"
    status, body = await _workflow_request("DELETE", url, api_key, session=session)
    if status >= 400 and status != 404:
        raise RuntimeError(f"Failed to delete novu workflow {workflow_id}: {body}")


def load_novu_workflow_templates(target_dir: str) -> dict[str, dict]:
    """Render every workflow template in the directory, keyed by workflow id.

    The templates hold no Jinja variables: the liquid the workflows render at trigger time
    uses `{{ }}`, which this environment does not treat as a placeholder, so it passes through.
    """
    template_env = get_env(template_path=target_dir)
    templates: dict[str, dict] = {}
    for _root, _dirs, files in os.walk(target_dir):
        for file in files:
            payload = ijson_loads(template_env.get_template(file).render())
            templates[payload["workflowId"]] = payload
    return templates


async def reconcile_novu_workflows(
    target_dir: str,
    config: AppSettings,
    api_key: str,
    session: aiohttp.ClientSession | None = None,
    templates: dict[str, dict] | None = None,
) -> None:
    """Make the environment's workflows match the templates exactly.

    Unlike the create-if-absent behaviour this replaces, an existing workflow is rewritten, so
    template fixes reach tenants that were provisioned before the fix.

    Pass `templates` to reuse an already-rendered set when reconciling several environments.
    """
    desired = templates if templates is not None else load_novu_workflow_templates(target_dir)
    live = {
        row["workflowId"]: row
        for row in await list_novu_workflows(config, api_key, session=session)
        if row.get("workflowId")
    }

    for workflow_id in sorted(set(live) - set(desired)):
        await delete_novu_workflow(workflow_id, config, api_key, session=session)
        log_info(f"Novu workflow {workflow_id} removed: no template defines it.")

    for workflow_id, payload in sorted(desired.items()):
        current = live.get(workflow_id)
        if current is None:
            await create_novu_workflow(payload, config, api_key, session=session)
            log_info(f"Novu workflow {workflow_id} created.")
        elif current.get("origin") == NOVU_CLOUD_ORIGIN:
            await replace_novu_workflow(workflow_id, payload, config, api_key, session=session)
            log_info(f"Novu workflow {workflow_id} updated.")
        else:
            # A v1 workflow cannot be upgraded in place: the v2 update leaves the origin at
            # novu-cloud-v1 and blanks the v1 templates it still renders from, which delivers
            # empty notifications. Recreating it is the only way to reach novu-cloud.
            await delete_novu_workflow(workflow_id, config, api_key, session=session)
            await create_novu_workflow(payload, config, api_key, session=session)
            log_info(f"Novu workflow {workflow_id} migrated from v1.")


def list_integration_provider(config: AppSettings, novu_api_key: str) -> list:
    """
    :return:
    """
    novu_client = IntegrationApi(url=config.dexit.novu_url, api_key=novu_api_key)
    response = novu_client.list()
    return [
        {
            "channel": res.channel,
            # /v1/integrations answers for the whole organization, not just the key's
            # environment, so callers have to filter on this to avoid seeing another
            # environment's providers as their own.
            "environment": getattr(res, "_environment_id", ""),
        }
        for res in response
    ]


def integrate_provider(
    provider: str,
    channel: str,
    credentials: dict,
    config: AppSettings,
    novu_api_key: str,
    active: bool = True,
) -> str:
    """
    :return:
    """
    novu_client = IntegrationApi(url=config.dexit.novu_url, api_key=novu_api_key)
    integration = {
        "provider_id": provider,
        "channel": channel,
        "credentials": credentials,
        "active": active,
    }
    integration = IntegrationDto(**integration)

    res = novu_client.create(
        integration=integration,
    )
    return res._id


def set_integration_provider_as_primary(integration_id: str, config: AppSettings, novu_api_key: str) -> None:
    """
    :param integration_id:
    :param config:
    :param novu_api_key:
    :return:
    """
    novu_client: IntegrationApi = IntegrationApi(url=config.dexit.novu_url, api_key=novu_api_key)
    novu_client.set_primary(integration_id)


def add_integration_provider(config: AppSettings, novu_api_key: str, environment_id: str = "") -> None:
    """
    Create the providers this environment is missing

    environment_id scopes the "already exists" check. Without it the listing returns every
    environment's providers, so provisioning a second environment sees the first one's email
    and chat integrations and silently creates neither.

    :return:
    """
    provider_data: list = list_integration_provider(config=config, novu_api_key=novu_api_key)
    if environment_id:
        provider_data = [item for item in provider_data if item.get("environment") == environment_id]

    email_exist: bool = False
    in_app_exist: bool = False
    chat_exist: bool = False
    for item in provider_data:
        if item.get("channel", "") == "email":
            email_exist = True
        if item.get("channel", "") == "in_app":
            in_app_exist = True
        if item.get("channel", "") == "chat":
            chat_exist = True

    # adding email provider sendgrid
    if not email_exist:
        integration_id = integrate_provider(
            provider="sendgrid",
            channel="email",
            credentials={
                "apiKey": config.sendgrid.api_key,
                "from": "developer@314ecorp.com",
                "senderName": "Dexit",
            },
            active=True,
            config=config,
            novu_api_key=novu_api_key,
        )

        if integration_id:
            set_integration_provider_as_primary(integration_id=integration_id, config=config, novu_api_key=novu_api_key)

    # adding in app provider novu
    if not in_app_exist:
        integrate_provider(
            provider="novu", channel="in_app", credentials={}, active=True, config=config, novu_api_key=novu_api_key
        )

    # adding slack chat provider
    if not chat_exist:
        integrate_provider(
            provider="slack",
            channel="chat",
            credentials={
                "applicationId": config.dexit.slack_application_id,
                "clientId": config.dexit.slack_client_id,
                "secretKey": config.dexit.slack_channel_secret_key,
            },
            active=True,
            config=config,
            novu_api_key=novu_api_key,
        )


class NovuSetup:
    """
    This class will be used to setup the Novu environment
    """

    def __init__(self: "NovuSetup", dexit: DexitSpec) -> None:
        self.dexit: DexitSpec = dexit
        self.config: AppSettings = get_settings()

    async def get_access_token(self: "NovuSetup", session: aiohttp.ClientSession | None = None) -> str:
        """
        Get the access token for the Novu environment
        """
        url = f"{self.config.dexit.novu_url}/v1/auth/login"

        payload = {"email": self.config.dexit.novu_admin_user, "password": self.config.dexit.novu_admin_password}

        async with _http(session) as http:
            async with http.post(url=url, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as response:
                if response.status >= 300:
                    raise aiohttp.ClientResponseError(
                        request_info=aiohttp.RequestInfo(
                            url=url,
                            method="POST",
                            headers={"Content-Type": HEADER_CONTENT_TYPE},
                        ),
                        history=(),
                        status=response.status,
                        message=f"Failed to get access token for Novu environment, status_code: {response.status}",
                    )

                response_json = await response.json()
                return response_json["data"]["token"]

    async def get_organizations_by_name(
        self: "NovuSetup", organization_name: str, token: str, session: aiohttp.ClientSession | None = None
    ) -> list:
        """
        List the organizations in the Novu environment
        """
        url = f"{self.config.dexit.novu_url}/v1/organizations"

        async with _http(session) as http:
            async with http.get(
                url=url, headers={"Authorization": f"Bearer {token}"}, timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                if response.status >= 300:
                    raise RuntimeError(f"Failed to get organization by name: {organization_name}")

                result = await response.json()
                return [row for row in result["data"] if row["name"] == organization_name]

    async def create_organization(
        self: "NovuSetup", token: str, org_name: str, session: aiohttp.ClientSession | None = None
    ) -> dict:
        """
        Create an organization in the Novu environment
        """
        url = f"{self.config.dexit.novu_url}/v1/organizations"

        payload = {
            "name": org_name,
        }

        async with _http(session) as http:
            async with http.post(
                url=url,
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as response:
                if response.status >= 300:
                    raise RuntimeError(f"Failed to create organization: {org_name}")

                return await response.json()

    async def get_organization_environments(
        self: "NovuSetup", token: str, session: aiohttp.ClientSession | None = None
    ) -> dict[str, dict]:
        """
        Get every environment of the organization, keyed by name

        Only Production is provisioned, but the whole set is returned so a missing Production
        is reported against what the organization actually has.
        """
        url = f"{self.config.dexit.novu_url}/v1/environments"

        async with _http(session) as http:
            async with http.get(
                url=url, headers={"Authorization": f"Bearer {token}"}, timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                if response.status >= 300:
                    raise RuntimeError(f"Failed to get API keys for organization status_code:{response.status}")

                result = await response.json()

        environments = {
            env.get("name"): {
                "api_key": env.get("apiKeys")[0].get("key"),
                "identifier": env.get("identifier", ""),
                "environment_id": env.get("_id", ""),
            }
            for env in result["data"]
            if env.get("name") and env.get("apiKeys")
        }

        if not environments.get(PRODUCTION_ENVIRONMENT, {}).get("api_key"):
            raise RuntimeError(
                f"Novu organization has no {PRODUCTION_ENVIRONMENT} api key; found {sorted(environments)}"
            )
        return environments

    async def connect_inbox(
        self: "NovuSetup", application_identifier: str, session: aiohttp.ClientSession | None = None
    ) -> None:
        """
        Open one Inbox session so the environment reports its in-app integration as connected

        Novu leaves a new environment's Inbox flagged as not connected until a client opens a
        session, which makes every in-app step show an integration warning in the dashboard.
        """
        url = f"{self.config.dexit.novu_url}/v1/inbox/session"
        payload = {"applicationIdentifier": application_identifier, "subscriberId": INBOX_CONNECT_SUBSCRIBER_ID}

        async with _http(session) as http:
            async with http.post(url=url, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as response:
                if response.status >= 300:
                    log_info(f"Inbox connect returned {response.status} for {application_identifier}; continuing.")

    async def switch_organization(
        self: "NovuSetup", organization_id: str, token: str, session: aiohttp.ClientSession | None = None
    ) -> str:
        """
        Switch the organization
        """
        url = f"{self.config.dexit.novu_url}/v1/auth/organizations/{organization_id}/switch"

        async with _http(session) as http:
            async with http.post(
                url=url, headers={"Authorization": f"Bearer {token}"}, timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                if response.status >= 300:
                    raise RuntimeError(f"Failed to switch organization: {organization_id}")

                result = await response.json()
                return result["data"]

    async def setup_novu(self: "NovuSetup") -> None:
        """
        Setup the Novu environment
        """
        config: AppSettings = get_settings()
        env: str = config.env
        server_item = "production-config" if env == "production" else "integration-config"

        organization_name = f"dexit_{self.dexit.tenant}"

        # One session for the whole activity. Provisioning makes roughly thirty requests, and
        # a session per request pays a TLS handshake on every one of them.
        async with aiohttp.ClientSession() as session:
            access_token = await self.get_access_token(session=session)
            organization = await self.get_organizations_by_name(
                organization_name=organization_name, token=access_token, session=session
            )
            if not organization:
                organization = await self.create_organization(
                    token=access_token, org_name=organization_name, session=session
                )
                organization_id = organization["data"]["id"]
                log_info(f"Novu Organization {organization_name} created successfully.")
            else:
                organization = organization[0]
                organization_id = organization["_id"]
                log_info(f"Novu Organization {organization_name} already exists; reusing it.")

            organization_token = await self.switch_organization(
                organization_id=organization_id, token=access_token, session=session
            )
            environments = await self.get_organization_environments(token=organization_token, session=session)
            production = environments[PRODUCTION_ENVIRONMENT]
            api_key = production["api_key"]

            # The tenant's application runs against Production, so this is the key it gets.
            await OnePasswordUtil(
                tenant=self.dexit.tenant,
                server_item=server_item,
                vault="Dexit",
            ).insert_if_not_exists(key="novu_api_key", value=api_key)

            # Production only. Development is left as Novu created it -- nothing triggers
            # against it, and an api key cannot reach outside its own environment anyway.
            novu_template_path = os.path.join(TemplatePath, "novu_workflow_template")
            await reconcile_novu_workflows(
                target_dir=novu_template_path, config=config, api_key=api_key, session=session
            )
            log_info(f"Novu Workflow templates reconciled successfully in {PRODUCTION_ENVIRONMENT}.")

            # The novu SDK is synchronous, so run it off the event loop rather than stalling
            # every other coroutine on this worker for the duration.
            await asyncio.to_thread(add_integration_provider, config, api_key, production["environment_id"])
            log_info(f"Integration provider added successfully in {PRODUCTION_ENVIRONMENT}.")

            if production["identifier"]:
                await self.connect_inbox(application_identifier=production["identifier"], session=session)


class DexitNovuSetupActivity(Activity):
    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity

        Twelve workflow creates plus the integrations. They usually run about a second each,
        but this endpoint spikes -- 40s and 85s have both been observed on an idle instance --
        so the ceiling is set well above the happy path.
        """
        return timedelta(seconds=600)

    @staticmethod
    @activity.defn(name="novu_setup_activity")
    async def defn(dexit: DexitSpec) -> None:
        """
        Callable for the activity
        """
        # Setup novu
        dexit_novu_setup = NovuSetup(dexit=dexit)
        await dexit_novu_setup.setup_novu()
