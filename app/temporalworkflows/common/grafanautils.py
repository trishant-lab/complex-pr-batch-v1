import requests

from app.core.settings import AppSettings, get_settings


class GrafanaUtils:
    def __init__(self):
        config: AppSettings = get_settings()
        self.grafana_url = config.grafana_url
        self.token = config.grafana_token

    def get_dashboard(self, dashboard_uid: str):
        headers = {
            "Authorization": f"Bearer {self.token}"
        }
        response = requests.get(f"{self.grafana_url}/api/dashboards/uid/{dashboard_uid}", headers=headers)
        return response.json()

    def update_dashboard(self, dashboard_json: dict):
        headers = {
            "Authorization": f"Bearer {self.token}"
        }
        response = requests.post(f"{self.grafana_url}/api/dashboards/db", headers=headers, json=dashboard_json)

        return response.json()

    def create_alerts(self, alert_json: dict):
        headers = {
            "Authorization": f"Bearer {self.token}"
        }
        response = requests.post(
            f"{self.grafana_url}/api/v1/provisioning/alert-rules/", headers=headers, json=alert_json
        )

        return response.json()
