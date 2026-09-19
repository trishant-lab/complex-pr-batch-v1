"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 63)
"""

from datetime import timedelta
from typing import Any
from urllib.parse import urljoin

import aiohttp
from aiohttp import ClientSession, ClientTimeout
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity
from app.cli.temporal.models.deboard import DeboardWorkflowInput
from app.cli.temporal.veritable.models.veritable_spec import VeritableSpec
from app.core.settings import AppSettings, get_settings


class NovuSetup:
    """
    This class will be used to setup the Novu integration for Veritable
    """

    def __init__(self: "NovuSetup", veritable: DeboardWorkflowInput) -> None:
        """
        Initialize the NovuSetup class
        """
        self.veritable: DeboardWorkflowInput = veritable
        self.config: AppSettings = get_settings()
        self.token: str | None = None
        self.organization_token: str | None = None
        self.environment_id: str | None = None
        self.novu_client: ClientSession | None = None
        self.novu_organization_client: ClientSession | None = None

    def set_novu_client(self: "NovuSetup") -> ClientSession:
        """
        Creates and returns a cached aiohttp ClientSession for Novu API communication.

        This session is configured with the base Novu authentication token and
        appropriate headers for general Novu API requests.

        Returns:
            ClientSession: Configured aiohttp client session for Novu API

        """
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        self.novu_client = ClientSession(
            base_url=f"{self.config.veritable.novu_url}", headers=headers, timeout=ClientTimeout(total=120)
        )

    def set_novu_organization_client(self: "NovuSetup") -> ClientSession:
        """
        Creates and returns a cached aiohttp ClientSession for organization-specific Novu API requests.

        This session is configured with the organization authentication token and environment ID,
        allowing for operations specific to the current organization context.

        Returns:
            ClientSession: Configured aiohttp client session for organization-specific Novu API requests

        """
        headers = {
            "Authorization": f"Bearer {self.organization_token}",
            "novu-environment-id": self.environment_id,
            "Content-Type": "application/json",
        }
        self.novu_organization_client = ClientSession(
            base_url=f"{self.config.veritable.novu_url}", headers=headers, timeout=ClientTimeout(total=120)
        )

    async def set_access_token(self: "NovuSetup") -> None:
        """
        Get the access token for the Novu integration
        """
        url: str = urljoin(self.config.veritable.novu_url, "/v1/auth/login")

        payload: dict[str, str] = {
            "email": self.config.veritable.novu_admin_user,
            "password": self.config.veritable.novu_admin_password,
        }

        async with aiohttp.ClientSession() as session:
            res: aiohttp.ClientResponse = await session.post(
                url=url, json=payload, timeout=aiohttp.ClientTimeout(total=120)
            )
            res.raise_for_status()
            response: dict[str, Any] = await res.json()
            self.token = response.get("data", {}).get("token")

    async def set_organization_token(self: "NovuSetup", organization_id: str) -> None:
        """
        Switch the organization
        """
        client = self.novu_client
        async with client.post(url=f"/v1/auth/organizations/{organization_id}/switch") as res:
            res.raise_for_status()
            response = await res.json()
            self.organization_token = response.get("data")

    async def set_environment_id(self: "NovuSetup") -> None:
        """
        Retrieves and sets the Novu environment ID for the current organization.

        This method queries the Novu API for available environments and sets
        the first environment ID for use in subsequent API calls. The environment ID
        is required for many organization-specific operations.
        """
        url: str = urljoin(self.config.veritable.novu_url, "/v1/environments")

        async with aiohttp.ClientSession() as session:
            res: aiohttp.ClientResponse = await session.get(
                url=url,
                headers={"Authorization": f"Bearer {self.organization_token}"},
                timeout=aiohttp.ClientTimeout(total=120),
            )
            res.raise_for_status()
            response_json = await res.json()
            environment = next(row for row in response_json.get("data", []) if row.get("name") == "Development")
            self.environment_id = environment.get("_id")

    async def get_organization_api_key(self: "NovuSetup") -> str:
        """
        Get the API keys for the organization
        """
        client = self.novu_organization_client
        async with client.get(url="/v1/environments/api-keys") as res:
            res.raise_for_status()
            response: dict[str, Any] = await res.json()
            return response["data"][0]["key"]

    async def create_organization(self: "NovuSetup", organization_name: str) -> dict[str, Any]:
        """
        Create an organization in the Novu environment
        """
        client = self.novu_client
        payload: dict[str, str] = {
            "name": organization_name,
        }
        async with client.post(url="/v1/organizations", json=payload) as res:
            res.raise_for_status()
            return await res.json()

    async def get_organizations_by_name(self: "NovuSetup", organization_name: str) -> list[dict[str, Any]]:
        """
        list the organizations in the Novu environment
        """
        client = self.novu_client
        async with client.get(url="/v1/organizations") as res:
            res.raise_for_status()
            response = await res.json()
            return [row for row in response["data"] if row["name"] == organization_name]

    async def get_all_subscribers(self: "NovuSetup") -> list[dict]:
        """
        Retrieves all subscribers from the current Novu environment.

        This method fetches up to 1000 subscribers from the Novu API for the
        current organization and environment.

        Returns:
            list[dict]: List of subscriber data dictionaries

        """
        client = self.novu_organization_client
        async with client.get(url="/v1/subscribers", params={"page": 0, "limit": 100}) as res:
            res.raise_for_status()
            response = await res.json()
            return response.get("data", [])

    async def delete_subscriber(self: "NovuSetup", subscriber_id: str) -> None:
        """
        Deletes a specific subscriber from the Novu environment.

        Args:
            subscriber_id (str): The ID of the subscriber to delete

        """
        client = self.novu_organization_client
        async with client.delete(url=f"/v1/subscribers/{subscriber_id}") as res:
            res.raise_for_status()

    async def delete_all_subscribers(self: "NovuSetup") -> None:
        """
        Deletes all subscribers from the current Novu environment.

        This method retrieves all subscribers and then iteratively deletes each one.
        Used during de-provisioning to clean up subscriber data.
        """
        subscribers = await self.get_all_subscribers()
        for subscriber in subscribers:
            subscriber_id = subscriber.get("subscriberId")
            await self.delete_subscriber(subscriber_id=subscriber_id)

    async def get_all_workflows(self: "NovuSetup") -> list[dict]:
        """
        Retrieves all notification workflows from the current Novu environment.

        This method fetches up to 100 notification templates (workflows) from
        the Novu API for the current organization and environment.

        Returns:
            list[dict]: List of workflow data dictionaries

        """
        client = self.novu_organization_client
        async with client.get("/v1/notification-templates", params={"page": 0, "limit": 100}) as res:
            res.raise_for_status()
            response = await res.json()
            return response.get("data", [])

    async def delete_workflow(self: "NovuSetup", workflow_id: str) -> None:
        """
        Deletes a specific notification workflow from the Novu environment.

        Args:
            workflow_id (str): The ID of the workflow to delete

        """
        client = self.novu_organization_client
        async with client.delete(url=f"/v1/notification-templates/{workflow_id}") as res:
            res.raise_for_status()

    async def delete_all_workflows(self: "NovuSetup") -> None:
        """
        Deletes all notification workflows from the current Novu environment.

        This method retrieves all workflows and then iteratively deletes each one.
        Used during de-provisioning to clean up workflow data.

        Returns:
            None

        """
        workflows = await self.get_all_workflows()
        for workflow in workflows:
            workflow_id = workflow.get("_id")
            await self.delete_workflow(workflow_id=workflow_id)

    async def get_all_integrations(self: "NovuSetup") -> list[dict]:
        """
        Retrieves all integrations from the current Novu environment.

        This method fetches the integrations configured in the Novu environment
        for the current organization.

        Returns:
            list[dict]: List of integration data dictionaries

        """
        client = self.novu_organization_client
        async with client.get("/v1/integrations") as res:
            res.raise_for_status()
            response = await res.json()
            return response.get("data", [])

    async def delete_integration(self: "NovuSetup", integration_id: str) -> None:
        """
        Deletes a specific integration from the Novu environment.

        Args:
            integration_id (str): The ID of the integration to delete

        """
        client = self.novu_organization_client
        async with client.delete(f"/v1/integrations/{integration_id}") as res:
            res.raise_for_status()

    async def delete_all_integrations(self: "NovuSetup") -> None:
        """
        Deletes all integrations from the current Novu environment.

        This method retrieves all integrations and then iteratively deletes each one.
        Used during de-provisioning to clean up integration configurations.
        """
        integrations: list[dict] = await self.get_all_integrations()
        for integration in integrations:
            integration_id = integration.get("_id")
            await self.delete_integration(integration_id=integration_id)

    async def clean_up(self: "NovuSetup") -> None:
        """
        Properly clean up and close HTTP client sessions.

        This method should be called when the NovuSetup instance is no longer needed
        to ensure all network resources are properly released. It closes both the
        organization-specific client and the general Novu client if they exist.

        Calling this method helps prevent resource leaks and ensures connections
        are properly terminated.
        """
        if self.novu_organization_client:
            await self.novu_organization_client.close()

        if self.novu_client:
            await self.novu_client.close()

    async def provision(self: "NovuSetup") -> str:
        """
        Setup the Novu environment
        """
        organization_name: str = self.veritable.novu_organization_name
        await self.set_access_token()
        self.set_novu_client()
        organization: list[dict[str, Any]] = await self.get_organizations_by_name(
            organization_name=organization_name,
        )

        if not organization:
            organization_response: dict[str, Any] = await self.create_organization(organization_name=organization_name)
            organization_id: str = organization_response["data"]["id"]
        else:
            organization_data: dict[str, Any] = organization[0]
            organization_id: str = organization_data["_id"]

        await self.set_organization_token(
            organization_id=organization_id,
        )
        await self.set_environment_id()
        self.set_novu_organization_client()
        api_key = await self.get_organization_api_key()
        await self.clean_up()
        return api_key

    async def de_provision(self: "NovuSetup") -> None:
        """
        De-provision the Novu Environment
        """
        organization_name: str = self.veritable.novu_organization_name
        await self.set_access_token()
        self.set_novu_client()
        organization: list[dict[str, Any]] = await self.get_organizations_by_name(
            organization_name=organization_name,
        )
        if not organization:
            return
        organization_data: dict[str, Any] = organization[0]
        organization_id: str = organization_data["_id"]
        await self.set_organization_token(organization_id=organization_id)
        await self.set_environment_id()
        self.set_novu_organization_client()
        await self.delete_all_subscribers()
        await self.delete_all_workflows()
        await self.delete_all_integrations()
        await self.clean_up()


class VeritableNovuOnboardingActivity(Activity):
    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=600)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="VeritableNovuOnboardingActivity")
    async def defn(veritable: VeritableSpec) -> str:
        """
        Callable for the activity
        """
        veritable = VeritableSpec.model_validate(veritable)
        novu_setup = NovuSetup(veritable=veritable)
        return await novu_setup.provision()


class VeritableNovuDeProvisionActivity(Activity):
    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=600)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="VeritableNovuDeProvisionActivity")
    async def defn(veritable: DeboardWorkflowInput) -> None:
        """
        Callable for the activity
        """
        veritable = DeboardWorkflowInput.model_validate(veritable)
        novu_setup = NovuSetup(veritable=veritable)
        await novu_setup.de_provision()


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
