import json
import os

import pytest

from app.cli.temporal.activities.grafana_dashboard import GrafanaDashboard, GrafanaDashboardProperties

TEMPLATE_DIR = os.path.join("app", "cli", "temporal", "zsegment", "templates")
TEMPLATES = ["grafana_dashboard_spring.json", "grafana_dashboard_camel.json", "grafana_dashboard_connector.json"]


def _dashboard(template: str, tenant: str = "acme") -> dict:
    grafana = GrafanaDashboard(
        GrafanaDashboardProperties(
            tenant=tenant,
            grafana_url="http://grafana:3000",
            api_key="unused",
            template_path=os.path.join(TEMPLATE_DIR, template),
            datasource_uid="vm-alerting",
        )
    )
    return grafana.prepare_dashboard(tenant)


@pytest.mark.parametrize("template", TEMPLATES)
def test_variables_are_hidden_on_every_template(template: str) -> None:
    """No template shows its variable pickers above the dashboard."""
    # The ZSegment UI embeds these and drives the variables through var-* URL
    # parameters, so Grafana's own dropdowns are a redundant second control.
    # hide=2 is Grafana's "Nothing" option for "Show on dashboard".
    variables = _dashboard(template)["templating"]["list"]

    assert variables, f"{template} is expected to have variables to hide"
    assert all(v["hide"] == 2 for v in variables), [(v["name"], v["hide"]) for v in variables]


@pytest.mark.parametrize("template", TEMPLATES)
def test_no_placeholder_survives_substitution(template: str) -> None:
    """Every <<dynamic_variable_*>> placeholder is replaced before the dashboard is sent."""
    rendered = json.dumps(_dashboard(template))

    assert "<<dynamic_variable_" not in rendered


def test_each_template_gets_its_own_title_and_uid() -> None:
    """A third template must not inherit the Camel title from the else branch."""
    spring = _dashboard("grafana_dashboard_spring.json")
    camel = _dashboard("grafana_dashboard_camel.json")
    connector = _dashboard("grafana_dashboard_connector.json")

    assert spring["title"] == "acme - Spring Boot 3.x Statistics"
    assert spring["uid"] == "spring_boot_acme"

    assert camel["title"] == "acme - Apache Camel - Context view"
    assert camel["uid"] == "apache-camel-micrometer-acme"

    assert connector["title"] == "acme - Connector"
    assert connector["uid"] == "zsegment-connector-acme"

    uids = {spring["uid"], camel["uid"], connector["uid"]}
    assert len(uids) == 3, f"dashboards would overwrite each other: {uids}"


def test_connector_panels_never_render_grafanas_no_data_text() -> None:
    """Every panel supplies its own placeholder for an absent series."""
    panels = [p for p in _dashboard("grafana_dashboard_connector.json")["panels"] if p.get("type") != "row"]

    assert panels
    without = [p.get("title") for p in panels if "noValue" not in p["fieldConfig"]["defaults"]]
    assert not without, without


def test_health_gauges_do_not_fall_back_to_zero() -> None:
    """A health or utilization gauge must read blank when absent, not 0.

    "Not reporting" and "zero" mean opposite things for these: a panel showing 0
    because nothing is reporting is a false all-clear. Counters are the
    exception - there 0 is the truth, so they carry `or vector(0)`.
    """
    panels = {
        p.get("title"): p for p in _dashboard("grafana_dashboard_connector.json")["panels"] if p.get("type") == "stat"
    }

    for title in ("Longest outage now", "Peak redial attempts", "CPU", "Memory", "Queue depth"):
        exprs = [t["expr"] for t in panels[title]["targets"]]
        assert all("or vector(0)" not in e for e in exprs), (title, exprs)

    for title in ("Sent upstream", "Dropped", "Connectors reporting", "Stream reconnects (1h)"):
        exprs = [t["expr"] for t in panels[title]["targets"]]
        assert all("or vector(0)" in e for e in exprs), (title, exprs)


def test_the_inventory_table_lists_every_connector() -> None:
    """The fleet table is not filtered by the connector picker.

    It exists to show which connectors exist, so scoping it to the current
    selection hides the rows a reader came for - and it is the panel someone
    checks when they suspect a connector is missing.
    """
    panels = [p for p in _dashboard("grafana_dashboard_connector.json")["panels"] if p.get("title") == "Connectors"]

    assert panels, "the fleet inventory table is expected to exist"
    for panel in panels:
        for target in panel["targets"]:
            assert "$connector" not in target["expr"], target["expr"]
            assert 'tenant="acme"' in target["expr"], target["expr"]


def test_connector_template_is_scoped_to_the_tenant() -> None:
    """The connector dashboard queries only the tenant it was provisioned for."""
    rendered = json.dumps(_dashboard("grafana_dashboard_connector.json", tenant="acme"))

    assert 'tenant=\\"acme\\"' in rendered
    assert "vm-alerting" in rendered


def test_unknown_template_does_not_silently_reuse_camel(tmp_path) -> None:
    """A new template without a kind branch must fail loud, not overwrite Camel."""
    import pytest
    from app.cli.temporal.activities.grafana_dashboard import (
        GrafanaDashboard,
        GrafanaDashboardProperties,
    )

    template = tmp_path / "grafana_dashboard_mystery.json"
    template.write_text(
        '{"title": "x", "uid": "y", "templating": {"list": []}, "panels": []}',
        encoding="utf-8",
    )
    props = GrafanaDashboardProperties(
        tenant="acme",
        grafana_url="http://grafana.test",
        api_key="k",
        template_path=str(template),
        datasource_uid="ds",
    )
    dash = GrafanaDashboard(props)
    with pytest.raises(ValueError, match="Unrecognized Grafana dashboard template"):
        dash.prepare_dashboard("acme")
