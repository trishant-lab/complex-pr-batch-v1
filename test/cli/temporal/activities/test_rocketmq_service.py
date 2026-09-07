from app.cli.temporal.activities.rocketmq_service import RocketMQProperties, build_mqadmin_script, topic_names

# Every topic zsegment-api or zsegment-engine addresses by name. The brokers run with
# autoCreateTopicEnable=false, so a topic missing here is a publish failure at runtime,
# not a topic the broker fills in.
EXPECTED_TOPICS = {
    "zsegment-acme-inbound",
    "zsegment-acme-outbound",
    "zsegment-acme-message-trace",
    "zsegment-acme-event",
    "zsegment-acme-event-response",
    "zsegment-acme-alert",
}


def test_covers_every_topic_the_apps_address() -> None:
    """A tenant is only fully provisioned once all six topics exist."""
    assert set(topic_names("acme")) == EXPECTED_TOPICS


def test_script_creates_each_topic_against_the_given_nameserver() -> None:
    """mqadmin takes a nameserver address, not the proxy the apps connect to."""
    properties = RocketMQProperties(
        tenant="acme", namespace="acme", name_server="nameserver.rocketmq.svc.cluster.local:9876"
    )

    script = build_mqadmin_script(properties)

    for topic in EXPECTED_TOPICS:
        assert topic in script
    assert "-n nameserver.rocketmq.svc.cluster.local:9876" in script
