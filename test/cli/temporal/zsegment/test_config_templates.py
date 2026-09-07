import json
import re

import pytest

from app.cli.temporal.zsegment import TemplatePath
from app.template_env import get_env

TEMPLATES = [
    "integration-api-config.tmpl.json",
    "integration-engine-config.tmpl.json",
    "production-api-config.tmpl.json",
    "production-engine-config.tmpl.json",
]

API_TEMPLATES = [name for name in TEMPLATES if "-api-" in name]

# Read by AlertConfig on the api. The contact point is deliberately absent: the code
# default is the only value we use, so pinning it here would be a second place to change.
EXPECTED_ALERT_KEYS = {
    "ALERT.GRAFANA_URL",
    "ALERT.GRAFANA_AUTH",
    "ALERT.GRAFANA_FOLDER_UID",
    "ALERT.GRAFANA_RULE_GROUP",
    "ALERT.GRAFANA_DATASOURCE_UID",
    "ALERT.GRAFANA_WEBHOOK_URL",
    "ALERT.TOPIC_RETENTION_HOURS",
    "ALERT.RULE_INTERVAL",
    "ALERT.FOR_DURATION",
    "ALERT.RULE_RECONCILE_INTERVAL_MS",
    "ALERT.NOTIFICATION_GROUP_BY",
    "ALERT.NOTIFICATION_GROUP_WAIT",
    "ALERT.NOTIFICATION_GROUP_INTERVAL",
    "ALERT.NOTIFICATION_REPEAT_INTERVAL",
}


def render(template_file_name: str, tenant: str = "acme") -> dict:
    """
    Render a template the way K8sConfigMapCreationActivity does, with a stand-in
    value for every variable it declares, and parse the result.

    Variables are discovered from the file rather than listed here so the test
    keeps checking the JSON after a new key is added to the payload.
    """
    raw = (get_env(TemplatePath).loader.get_source(get_env(TemplatePath), template_file_name))[0]
    payload = {name: f"{name}-value" for name in set(re.findall(r"<<\s*(\w+)\s*>>", raw))}
    payload["tenantName"] = tenant

    return json.loads(get_env(TemplatePath).get_template(template_file_name).render(**payload))


@pytest.mark.parametrize("template_file_name", TEMPLATES)
def test_renders_to_valid_json(template_file_name: str) -> None:
    """A stray comma leaves the pod with an unparseable SPRING_APPLICATION_JSON."""
    assert render(template_file_name)


@pytest.mark.parametrize("template_file_name", API_TEMPLATES)
def test_api_templates_carry_the_alert_keys(template_file_name: str) -> None:
    """A key absent here silently falls back to the api default."""
    config = render(template_file_name)

    assert {key for key in config if key.startswith("ALERT.")} == EXPECTED_ALERT_KEYS


@pytest.mark.parametrize("template_file_name", API_TEMPLATES)
def test_alert_rule_group_and_webhook_are_per_tenant(template_file_name: str) -> None:
    """
    Grafana keys the rule group by name inside the folder, and all tenants share the
    zsegment folder, so a fixed group name would have one tenant's sync overwrite
    another's rules.
    """
    config = render(template_file_name, tenant="acme")

    assert config["ALERT.GRAFANA_RULE_GROUP"] == "zsegment-alerts-acme"
    assert config["ALERT.GRAFANA_WEBHOOK_URL"] == (
        "http://zsegment-api.acme.svc.cluster.local:8090/api/v1/alerts/webhook"
    )


@pytest.mark.parametrize(
    ("template_file_name", "item"),
    [
        ("integration-api-config.tmpl.json", "zsegment-appgrafana-integration-sa"),
        ("production-api-config.tmpl.json", "zsegment-appgrafana-production-sa"),
    ],
)
def test_alert_auth_reads_the_environment_service_account(template_file_name: str, item: str) -> None:
    """
    The token is injected by `op inject` after rendering, so the reference has to
    survive jinja untouched and carry the Bearer prefix the api sends verbatim.
    """
    config = render(template_file_name)

    assert config["ALERT.GRAFANA_AUTH"] == f"Bearer {{{{ op://zsegment/{item}/password }}}}"


@pytest.mark.parametrize("template_file_name", API_TEMPLATES)
def test_alert_datasource_uid_comes_from_the_payload(template_file_name: str) -> None:
    """The alerting datasource must be the one the dashboards already use."""
    config = render(template_file_name)

    assert config["ALERT.GRAFANA_DATASOURCE_UID"] == "grafanaDatasourceUid-value"
