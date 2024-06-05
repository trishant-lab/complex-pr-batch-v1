import orjson
from loguru import logger

from app.cli.common.grafanaUtils import GrafanaUtils
from app.cli.veritable import TemplatePath
from app.cli.veritable.models.veritableSpec import VeritableSpec
from app.core.settings import get_settings, VeritableSettings
from app.template_env import get_env


def convert_to_binary(input_string):
    binary_string = ''.join(format(ord(c), '08b') for c in input_string)
    binary_number = int(binary_string, 2)
    return binary_number


async def create_grafana_alerts(veritable: VeritableSpec):
    """
    Create Grafana alerts
    """
    logger.info(f"Creating Grafana alerts for {veritable.tenant}")

    # create grafana alerts
    template_env = get_env(template_path=TemplatePath)
    alert_template = template_env.get_template("grafana_alerts.json")
    alerts = alert_template.render(
        tenant=veritable.tenant
    )

    grafana_utils = GrafanaUtils()
    grafana_utils.create_alerts(orjson.loads(alerts))

    logger.info(f"Grafana Alerts created for {veritable.tenant}")
