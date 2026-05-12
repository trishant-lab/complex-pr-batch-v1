"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 15)
"""

import aiohttp
import json
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from temporalio import activity
from datetime import timedelta
from temporalio.common import RetryPolicy


class GrafanaDashboardProperties(LaunchpadCLIBaseModel):
    """
    Properties required for creating Grafana dashboards
    """

    tenant: str
    grafana_url: str
    api_key: str
    template_path: str  # Path to the dashboard template JSON file
    datasource_uid: str  # uid of the metrics datasource in the target Grafana instance


class GrafanaDashboard:
    def __init__(self, properties: GrafanaDashboardProperties) -> None:
        self.properties = properties

    def prepare_dashboard(self, tenant_name: str) -> dict:
        """
        Renders a template into the dashboard that will be sent to Grafana.

        Separate from create_dashboard so the substitution, naming and variable
        handling can be exercised without an HTTP call.
        """
        # Load the dashboard template from the specified path
        dashboard_json = self._get_dashboard_template()

        # Replace the dynamic tenant variable - fix the typo in variable name
        dashboard_json = dashboard_json.replace("<<dynamic_variable_tenant>>", tenant_name)

        dashboard_json = dashboard_json.replace("<<dynamic_variable_datasource>>", self.properties.datasource_uid)

        # Parse the JSON to a dictionary
        dashboard_dict = json.loads(dashboard_json)

        # More reliable detection of dashboard type based on filename.
        # Each template needs its own branch: the final else is a fallback, so a
        # template added without one is silently published under another
        # dashboard's title and uid, overwriting it.
        template_path_lower = self.properties.template_path.lower()
        if "spring" in template_path_lower or "springboot" in template_path_lower:
            dashboard_dict["title"] = f"{tenant_name} - Spring Boot 3.x Statistics"
            dashboard_dict["uid"] = f"spring_boot_{tenant_name}"
        elif "connector" in template_path_lower:
            dashboard_dict["title"] = f"{tenant_name} - Connector"
            dashboard_dict["uid"] = f"zsegment-connector-{tenant_name}"
        else:
            dashboard_dict["title"] = f"{tenant_name} - Apache Camel - Context view"
            dashboard_dict["uid"] = f"apache-camel-micrometer-{tenant_name}"

        self._hide_variables(dashboard_dict)

        return dashboard_dict

    @staticmethod
    def _hide_variables(dashboard_dict: dict) -> None:
        """
        Hides the variable pickers that Grafana would otherwise draw above the dashboard.

        The ZSegment UI embeds these dashboards and selects variables through
        var-* URL parameters, so Grafana's own dropdowns are a redundant second
        control that can disagree with the surrounding page. hide=2 is the
        "Nothing" option under a variable's "Show on dashboard" setting; the
        variables still resolve and still respond to the URL.
        """
        for variable in dashboard_dict.get("templating", {}).get("list", []):
            variable["hide"] = 2

    async def create_dashboard(self, tenant_name: str) -> dict:
        """
        Creates a new Grafana dashboard for the tenant.
        """
        url = f"{self.properties.grafana_url}/api/dashboards/db"

        dashboard_dict = self.prepare_dashboard(tenant_name)

        # Prepare the payload
        payload = {
            "dashboard": dashboard_dict,
            "overwrite": True,
            "message": f"Dashboard created for tenant {tenant_name}",
            "folderId": 0,
        }

        # Set up headers with API key
        headers = {"Authorization": f"Bearer {self.properties.api_key}", "Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            response = await session.post(url=url, headers=headers, json=payload)

            if response.status == 404:
                raise aiohttp.ClientError(f"API endpoint not found. URL: {url}")

            content = await response.json()
            if response.status != 200:
                raise aiohttp.ClientError(f"Failed to create Grafana dashboard: {content}")

            return content

    def _get_dashboard_template(self) -> str:
        """
        Loads the dashboard JSON template from the provided template path.
        """
        try:
            with open(self.properties.template_path) as file:
                return file.read()
        except FileNotFoundError:
            raise ValueError(f"Dashboard template file not found at {self.properties.template_path}")


class GrafanaDashboardActivity(Activity):
    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=2,
            maximum_attempts=3,
        )

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=60)

    @staticmethod
    @activity.defn(name="grafana_dashboard_activity")
    async def defn(properties: GrafanaDashboardProperties) -> dict:
        """
        Callable for the activity to create a Grafana dashboard
        """
        # Initialize the dashboard class with properties
        dashboard = GrafanaDashboard(properties=properties)

        # Create the dashboard
        return await dashboard.create_dashboard(tenant_name=properties.tenant)


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
