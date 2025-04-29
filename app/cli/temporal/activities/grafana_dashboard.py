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


class GrafanaDashboard:
    def __init__(self, properties: GrafanaDashboardProperties) -> None:
        self.properties = properties

    async def create_dashboard(self, tenant_name: str) -> dict:
        """
        Creates a new Grafana dashboard for the tenant.
        """
        url = f"{self.properties.grafana_url}/api/dashboards/db"

        # Load the dashboard template from the specified path
        dashboard_json = self._get_dashboard_template()

        # Replace the dynamic tenant variable
        dashboard_json = dashboard_json.replace("{{dynamic_varialbe_tenant}}", f'"{tenant_name}"')

        # Parse the JSON to a dictionary
        dashboard_dict = json.loads(dashboard_json)

        # Prepare the payload
        payload = {
            "dashboard": dashboard_dict,
            "overwrite": True,
            "message": f"Dashboard created for tenant {tenant_name}",
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
