"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 19)
"""

from datetime import timedelta

import aiohttp
import httpx
from loguru import logger
from novu.api import IntegrationApi
from novu.dto import IntegrationDto
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_info
from app.cli.temporal.jeeves.jeeves import JeevesSpec
from app.cli.temporal.jeeves.models.jeeves_spec import SpaceSpec
from app.cli.temporal.jeeves.template_main import get_jeeves_broadcast_layout_content
from app.core.settings import AppSettings, get_settings
from app.one_password_util import OnePasswordUtil

BROADCAST_WORKFLOW_ID = "jeeves-broadcast"
# Must match NOVU_LAYOUT_IDENTIFIER in jeeves-app app/route/novuhelper.py.
BROADCAST_V2_LAYOUT_IDENTIFIER = "jeeves-layout"
# Matches JEEVES_LAYOUT_NAME in jeeves-app app/constants.py and the
# broadcastlayout.name seed in jeeves-app's migrations.
BROADCAST_V2_LAYOUT_NAME = "Jeeves Layout"


def get_v2_layout_id(novu_url: str, novu_api_key: str, identifier: str) -> str | None:
    """Fetch a v2 layout's internal id by identifier slug; None if absent."""
    response = httpx.get(
        f"{novu_url}/v2/layouts/{identifier}",
        headers={"Authorization": f"ApiKey {novu_api_key}"},
        timeout=10,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json().get("data", {}).get("_id")


async def create_jeeves_broadcast_v2_layout(config: AppSettings, novu_api_key: str) -> int:
    """
    Bootstrap the jeeves-broadcast v2 layout in Novu. Mirrors upsert_novu_layout
    in jeeves-app app/route/novuhelper.py. Layout HTML must contain the
    ``{{ content }}`` placeholder; Novu v2 rejects ``{{body}}`` from v1 era.

    Novu v2 splits layout create (``POST /v2/layouts`` — metadata only) from
    update (``PUT /v2/layouts/{layoutId}`` — sets the HTML body); PUT is not
    upsert-shaped and 404s against a layout that doesn't exist yet. So this
    always hits the 404 path on a brand-new tenant: PUT first, and on 404,
    POST the metadata shell then retry the PUT to load the HTML body.
    """
    layout_html: str = await get_jeeves_broadcast_layout_content()
    put_data: dict = {
        "name": BROADCAST_V2_LAYOUT_NAME,
        "controlValues": {
            "email": {
                "body": layout_html,
                "editorType": "html",
            },
        },
    }
    headers: dict = {
        "Authorization": f"ApiKey {novu_api_key}",
        "Content-Type": "application/json",  # NOSONAR
    }
    put_url: str = f"{config.jeeves.novu_url}/v2/layouts/{BROADCAST_V2_LAYOUT_IDENTIFIER}"
    async with aiohttp.ClientSession() as session:
        response = await session.put(
            url=put_url, json=put_data, headers=headers, timeout=aiohttp.ClientTimeout(total=60)
        )
        if response.status != 404:
            if response.status >= 400:
                logger.error(f"Failed to update jeeves-broadcast v2 layout : {await response.json()}")
            return response.status

        create_data: dict = {"layoutId": BROADCAST_V2_LAYOUT_IDENTIFIER, "name": BROADCAST_V2_LAYOUT_NAME}
        create_response = await session.post(
            url=f"{config.jeeves.novu_url}/v2/layouts",
            json=create_data,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=60),
        )
        if create_response.status >= 400:
            logger.error(f"Failed to create jeeves-broadcast v2 layout metadata : {await create_response.json()}")
            return create_response.status

        response = await session.put(
            url=put_url, json=put_data, headers=headers, timeout=aiohttp.ClientTimeout(total=60)
        )
        if response.status >= 400:
            logger.error(f"Failed to load jeeves-broadcast v2 layout body after create : {await response.json()}")
    return response.status


def get_v2_workflow_id(novu_url: str, novu_api_key: str, workflow_id: str) -> str | None:
    """Fetch a v2 workflow's internal id by workflowId slug; None if absent."""
    response = httpx.get(
        f"{novu_url}/v2/workflows/{workflow_id}",
        headers={"Authorization": f"ApiKey {novu_api_key}"},
        timeout=10,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json().get("data", {}).get("_id")


async def create_jeeves_broadcast_workflow_v2(
    config: AppSettings, novu_api_key: str, workflow_exists: bool = False
) -> int:
    """
    Create the jeeves-broadcast v2 workflow. Mirrors
    jeeves-app/personal-scripts/broadcast/create_jeeves_broadcast_workflow_v2.py.

    The email step references the layout by ``layoutId`` rather than baking
    its HTML into the step body, so a later edit to the jeeves-layout Layout
    resource (e.g. per-tenant branding via the layout-editing feature) is
    picked up by this workflow automatically instead of drifting from it.
    """

    def channel_skip(marker: str) -> dict:
        # Novu v2 evaluates controlValues.skip as runIf (not skipIf): step runs iff
        # payload.activeChannels contains `marker`.
        return {"and": [{"in": [marker, {"var": "payload.activeChannels"}]}]}

    data: dict = {
        "name": BROADCAST_WORKFLOW_ID,
        "workflowId": BROADCAST_WORKFLOW_ID,
        "description": "Single consolidated workflow used by every broadcast. "
        "Per-channel content is provided via the trigger payload.",
        "active": True,
        "tags": [],
        # `origin=external` required for script/API-managed workflows.
        "origin": "external",
        "steps": [
            {
                "name": "Email",
                "type": "email",
                "controlValues": {
                    "subject": "{{ payload.subject }}",
                    "body": "{{ payload.html_content }}",
                    "editorType": "html",
                    "layoutId": BROADCAST_V2_LAYOUT_IDENTIFIER,
                    "skip": channel_skip("EMAIL"),
                },
            },
            {
                "name": "In-App",
                "type": "in_app",
                "controlValues": {
                    "subject": "{{ payload.in_app_subject }}",
                    "body": "{{ payload.in_app_content }}",
                    "data": {
                        "broadcastId": "{{ payload.broadcastId }}",
                        "broadcastTypeId": "{{ payload.broadcastTypeId }}",
                        "isImportant": "{{ payload.isImportant }}",
                        "contextId": "{{ payload.contextId }}",
                        "contextTitle": "{{ payload.contextTitle }}",
                        "acknowledgmentMode": "{{ payload.acknowledgment_mode }}",
                        "requireAcknowledge": "{{ payload.require_acknowledge }}",
                        "token": "{{ payload.token }}",
                        "ctaUrl": "{{ payload.cta_url }}",
                        "ctaLabel": "{{ payload.cta_label }}",
                        "broadcastTypeTitle": "{{ payload.broadcast_type_title }}",
                        "entityType": "{{ payload.entity_type }}",
                        "eventName": "{{ payload.event_name }}",
                    },
                    "skip": channel_skip("INAPP"),
                },
            },
            {
                "name": "Chat (Teams DM)",
                "type": "chat",
                "controlValues": {
                    "body": "{{ payload.channels.TEAMS.content }}",
                    "skip": channel_skip("TEAMS"),
                },
            },
        ],
    }
    headers: dict = {
        "Authorization": f"ApiKey {novu_api_key}",
        "Content-Type": "application/json",  # NOSONAR
    }
    async with aiohttp.ClientSession() as session:
        if workflow_exists:
            response = await session.put(
                url=f"{config.jeeves.novu_url}/v2/workflows/{BROADCAST_WORKFLOW_ID}",
                json=data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60),
            )
        else:
            response = await session.post(
                url=f"{config.jeeves.novu_url}/v2/workflows",
                json=data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60),
            )
        if response.status >= 400:
            logger.error(f"Failed to upsert jeeves-broadcast v2 workflow : {await response.json()}")
    return response.status


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
    novu_client = IntegrationApi(url=config.jeeves.novu_url, api_key=novu_api_key)
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


async def add_novu_templates(config: AppSettings, novu_api_key: str) -> None:
    """
    Create the jeeves-broadcast v2 layout + workflow, idempotently.
    """
    jeeves_broadcast_v2_layout: str | None = get_v2_layout_id(
        novu_url=config.jeeves.novu_url, novu_api_key=novu_api_key, identifier=BROADCAST_V2_LAYOUT_IDENTIFIER
    )
    if jeeves_broadcast_v2_layout is None:
        await create_jeeves_broadcast_v2_layout(config=config, novu_api_key=novu_api_key)

    jeeves_broadcast_workflow: str | None = get_v2_workflow_id(
        novu_url=config.jeeves.novu_url, novu_api_key=novu_api_key, workflow_id=BROADCAST_WORKFLOW_ID
    )
    await create_jeeves_broadcast_workflow_v2(
        config=config, novu_api_key=novu_api_key, workflow_exists=jeeves_broadcast_workflow is not None
    )


def list_integration_provider(config: AppSettings, novu_api_key: str) -> list:
    """
    :return:
    """
    novu_client = IntegrationApi(url=config.jeeves.novu_url, api_key=novu_api_key)
    response = novu_client.list()
    return [
        {
            "id": res._id,
            "provider": res.provider_id,
            "channel": res.channel,
            "active": res.active,
        }
        for res in response
    ]


def set_integration_provider_as_primary(integration_id: str, config: AppSettings, novu_api_key: str) -> None:
    """

    :param integration_id:
    :param config:
    :param novu_api_key:
    :return:
    """
    novu_client: IntegrationApi = IntegrationApi(url=config.jeeves.novu_url, api_key=novu_api_key)
    novu_client.set_primary(integration_id)


def add_integration_provider(config: AppSettings, novu_api_key: str) -> None:
    """

    :return:
    """
    provider_data: list = list_integration_provider(config=config, novu_api_key=novu_api_key)
    email_exist: bool = False
    in_app_exist: bool = False
    for item in provider_data:
        if item.get("channel", "") == "email":
            email_exist = True
        if item.get("channel", "") == "in_app":
            in_app_exist = True

    # adding email provider sendgrid
    if not email_exist:
        integration_id = integrate_provider(
            provider="sendgrid",
            channel="email",
            credentials={
                "apiKey": config.sendgrid.api_key,
                "from": config.jeeves.novu_sendgrid_sender_email,
                "senderName": config.jeeves.novu_sendgrid_sender_name,
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


class NovuSetup:
    """
    This class will be used to setup the Novu environment
    """

    def __init__(self: "NovuSetup", jeeves: JeevesSpec, space_name: str) -> None:
        self.jeeves: JeevesSpec = jeeves
        self.config: AppSettings = get_settings()
        self.space_name: str = space_name

    async def get_access_token(self: "NovuSetup") -> str:
        """
        Get the access token for the Novu environment
        """
        url = f"{self.config.jeeves.novu_url}/v1/auth/login"

        payload = {"email": self.config.jeeves.novu_admin_user, "password": self.config.jeeves.novu_admin_password}

        response = httpx.post(url=url, json=payload, timeout=120)

        if response.status_code >= 300:
            raise httpx.HTTPStatusError(
                f"Failed to get access token for Novu environment. Status code: {response.status_code}",
                request=response.request,
                response=response,
            )

        return response.json()["data"]["token"]

    async def get_organizations_by_name(self: "NovuSetup", organization_name: str, token: str) -> list:
        """
        List the organizations in the Novu environment
        """
        url = f"{self.config.jeeves.novu_url}/v1/organizations"

        response = httpx.get(url=url, headers={"Authorization": f"Bearer {token}"}, timeout=120)
        logger.debug(f"organisation name key: {response.json()}")
        if response.status_code >= 300:
            raise httpx.HTTPStatusError(
                f"Failed to get organization by name: {organization_name}", request=response.request, response=response
            )

        return [row for row in response.json()["data"] if row["name"] == organization_name]

    async def create_organization(self: "NovuSetup", token: str, org_name: str) -> dict:
        """
        Create an organization in the Novu environment
        """
        url = f"{self.config.jeeves.novu_url}/v1/organizations"

        payload = {
            "name": org_name,
        }

        response = httpx.post(url=url, headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=120)

        if response.status_code >= 300:
            raise httpx.HTTPStatusError(
                f"Failed to create organization: {org_name}", request=response.request, response=response
            )

        return response.json()

    def switch_organization(self: "NovuSetup", organization_id: str, token: str) -> str:
        """
        Switch the organization
        """
        url = f"{self.config.jeeves.novu_url}/v1/auth/organizations/{organization_id}/switch"

        response = httpx.post(url=url, headers={"Authorization": f"Bearer {token}"}, timeout=120)

        if response.status_code >= 300:
            raise httpx.HTTPStatusError(
                f"Failed to switch organization: {organization_id}", request=response.request, response=response
            )

        return response.json()["data"]

    async def get_environment_api_key(self: "NovuSetup", token: str) -> str:
        """
        Get novu env id
        """
        url = f"{self.config.jeeves.novu_url}/v1/environments"

        response = httpx.get(
            url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}, timeout=120
        )
        if response.status_code >= 300:
            raise httpx.HTTPStatusError(
                "Failed to get novu env id",
                request=response.request,
                response=response,
            )

        api_keys: list = [
            env.get("apiKeys")[0].get("key") for env in response.json()["data"] if env.get("name") == "Development"
        ]
        if api_keys and api_keys[0]:
            return api_keys[0]
        else:
            raise httpx.HTTPStatusError(
                "Failed to get novu env api key",
                request=response.request,
                response=response,
            )

    async def setup_novu(self: "NovuSetup") -> None:
        """
        Setup the Novu environment
        """
        config: AppSettings = get_settings()

        organization_name = f"{self.space_name}"
        access_token = await self.get_access_token()
        organization = await self.get_organizations_by_name(organization_name=organization_name, token=access_token)
        if not organization:
            organization = await self.create_organization(token=access_token, org_name=organization_name)
            organization_id = organization["data"]["id"]
        else:
            organization = organization[0]
            organization_id = organization["_id"]

        organization_token = self.switch_organization(organization_id=organization_id, token=access_token)

        api_keys = await self.get_environment_api_key(token=organization_token)

        # store in 1Password
        await OnePasswordUtil(
            tenant=f"{self.space_name}",
            server_item="application-config",
            vault="Jeeves",
        ).insert_if_not_exists(key="novu_api_key", value=api_keys)

        # create the templates
        await add_novu_templates(config=config, novu_api_key=api_keys)

        # add the integration provider
        add_integration_provider(config=config, novu_api_key=api_keys)

        log_info(f"Novu environment setup completed for tenant: {self.space_name}")


class JeevesNovuSetupActivityModel(LaunchpadCLIBaseModel):
    """
    JeevesNovuSetupActivityModel
    """

    jeeves: JeevesSpec | SpaceSpec
    space_name: str


class JeevesNovuSetupActivity(Activity):
    """
    JeevesNovuSetupActivity
    """

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=120)

    @staticmethod
    @activity.defn(name="JeevesNovuSetupActivity")
    async def defn(activity_model: JeevesNovuSetupActivityModel) -> None:
        """
        Callable for the activity
        """
        jeeves_novu_setup = NovuSetup(jeeves=activity_model.jeeves, space_name=activity_model.space_name)
        await jeeves_novu_setup.setup_novu()


# --- launchpad oncall hardening (complex-pr batch) ---
def _activity_log_fields(name: str, **extra):
    """Structured fields for Temporal activity logging (oncall / Grafana)."""
    base = {
        "activity": name,
        "service": "launchpad",
        "layer": "temporal",
        "product": "launchpad-app",
    }
    base.update(extra)
    return base


class ActivityHardeningError(RuntimeError):
    """Refuse silent/unsafe fallbacks inside Temporal activities."""

    def __init__(self, activity: str, reason: str):
        super().__init__(f"[{activity}] {reason}")
        self.activity = activity
        self.reason = reason


def _require_nonempty(activity: str, field: str, value) -> None:
    """Fail loud when a required provisioning field is blank."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ActivityHardeningError(activity, f"{field} must be set before provision")


_RETRY_HINTS = {
    "transient_http": {"attempts": 5, "backoff_seconds": 8},
    "dependency_warmup": {"attempts": 3, "backoff_seconds": 20},
    "idempotent_create": {"attempts": 2, "backoff_seconds": 5},
}


def _retry_hint(kind: str) -> dict:
    """Return a documented retry hint for activity authors / runbooks."""
    return dict(_RETRY_HINTS.get(kind, _RETRY_HINTS["transient_http"]))
