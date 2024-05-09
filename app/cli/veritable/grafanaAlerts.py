import orjson
from loguru import logger

from app.cli.veritable import TemplatePath
from app.core.settings import ProductConfig, get_settings
from app.template_env import get_env
from app.cli.common.grafanaUtils import GrafanaUtils
from app.cli.veritable.common import VeritableSpec, ProductName


def convert_to_binary(input_string):
    binary_string = ''.join(format(ord(c), '08b') for c in input_string)
    binary_number = int(binary_string, 2)
    return binary_number


async def create_grafana_alerts(veritable: VeritableSpec):
    """
    Create Grafana alerts
    """
    logger.info(f"Creating Grafana alerts for {veritable.tenant}")

    product_config: ProductConfig = get_settings().product_config.get(ProductName)

    worker_beat_panel_id = str(convert_to_binary(veritable.tenant))
    server_panel_id = "1" + worker_beat_panel_id
    worker_count_panel_id = "2" + worker_beat_panel_id

    # create grafana panels
    grafana_utils = GrafanaUtils()
    current_dashboard = grafana_utils.get_dashboard(dashboard_uid=product_config.grafana.dashboard_uid)

    current_panels = current_dashboard.get("dashboard", {}).get("panels", [])

    modified_panels = []
    template_env = get_env(template_path=TemplatePath)
    # grafana worker beat panel
    worker_beat_panel_template = template_env.get_template("grafana_worker_beat_pannel.json")
    worker_beat_panel = worker_beat_panel_template.render(
        tenant=veritable.tenant, PanelID=worker_beat_panel_id, DatasourceUID=product_config.grafana.datasource_uid
    )
    modified_panels.append(orjson.loads(worker_beat_panel))

    # grafana worker count pannel
    worker_count_panel_template = template_env.get_template("grafana_worker_count_pannel.json")
    worker_count_panel = worker_count_panel_template.render(
        tenant=veritable.tenant, PanelID=worker_count_panel_id, DatasourceUID=product_config.grafana.datasource_uid
    )
    modified_panels.append(orjson.loads(worker_count_panel))

    # grafana server pannel
    server_panel_template = template_env.get_template("grafana_server_pannel.json")
    server_panel = server_panel_template.render(
        tenant=veritable.tenant, PanelID=server_panel_id, DatasourceUID=product_config.grafana.datasource_uid
    )
    modified_panels.append(orjson.loads(server_panel))

    new_panels = [
        panel for panel in current_panels
        if panel.get("title") not in [new_element.get("title") for new_element in modified_panels]
    ]

    new_panels.extend(modified_panels)

    current_dashboard["dashboard"]["panels"] = new_panels

    grafana_utils.update_dashboard(dashboard_json=current_dashboard)

    logger.info(f"Grafana Panels created for {veritable.tenant}")

    # Alert for worker beat
    worker_beat_alert_template = template_env.get_template("grafana_worker_beat_alerts.json")
    worker_beat_alert = worker_beat_alert_template.render(
        tenant=veritable.tenant, DatasourceUID=product_config.grafana.datasource_uid, PannelID=worker_beat_panel_id,
        FolderUID=product_config.grafana.alert_folder_uid, DashboardUID=product_config.grafana.dashboard_uid
    )
    grafana_utils.create_alerts(orjson.loads(worker_beat_alert))

    # Alert for worker count
    worker_count_alert_template = template_env.get_template("grafana_worker_count_alerts.json")
    worker_count_alert = worker_count_alert_template.render(
        tenant=veritable.tenant, DatasourceUID=product_config.grafana.datasource_uid, PannelID=worker_count_panel_id,
        FolderUID=product_config.grafana.alert_folder_uid, DashboardUID=product_config.grafana.dashboard_uid
    )
    grafana_utils.create_alerts(orjson.loads(worker_count_alert))

    # Alert for server
    server_alert_template = template_env.get_template("grafana_server_alerts.json")
    server_alert = server_alert_template.render(
        tenant=veritable.tenant, DatasourceUID=product_config.grafana.datasource_uid, PannelID=server_panel_id,
        FolderUID=product_config.grafana.alert_folder_uid, DashboardUID=product_config.grafana.dashboard_uid
    )
    grafana_utils.create_alerts(orjson.loads(server_alert))

    logger.info(f"Grafana Alerts created for {veritable.tenant}")
