"""
ZSegment Temporal CLI
"""

from os import path

TemplatePath = path.abspath(path.join(path.dirname(__file__), "templates"))

# The apps connect to the proxy over gRPC; mqadmin only accepts a nameserver address.
# Each environment is a separate cluster, so the service names are identical in both.
RocketMQEndpoints = {
    "integration": {
        "proxy": "rocketmq-c89ee107-proxy.rocketmq.svc.cluster.local:8080",
        "name_server": "rocketmq-c89ee107-nameserver.rocketmq.svc.cluster.local:9876",
    },
    "production": {
        "proxy": "rocketmq-c89ee107-proxy.rocketmq.svc.cluster.local:8080",
        "name_server": "rocketmq-c89ee107-nameserver.rocketmq.svc.cluster.local:9876",
    },
}

# The uid of the metrics datasource differs per Grafana instance.
GrafanaDatasourceUids = {
    "integration": "fec8h5fj8a2o0a",
    "production": "feewqunygt6v4a",
}
