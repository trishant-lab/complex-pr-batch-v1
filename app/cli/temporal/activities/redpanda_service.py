from datetime import timedelta
from temporalio import activity
from temporalio.common import RetryPolicy
from concurrent.futures import wait, ALL_COMPLETED

import httpx
from confluent_kafka.admin import (
    AdminClient,
    AclBinding,
    AclOperation,
    AclPermissionType,
    ResourceType,
    ResourcePatternType,
)
from confluent_kafka import KafkaError

from confluent_kafka.cimpl import NewTopic

from app.cli.temporal.core.base import LaunchpadCLIBaseModel, Activity
from app.cli.temporal.core.log import log_error, log_info


class RedpandaProperties(LaunchpadCLIBaseModel):
    tenant: str
    environment: None | str = None
    broker: str = "localhost:9092"
    security_protocol: str = "SASL_PLAINTEXT"
    admin_username: None | str = None
    admin_password: None | str = None
    admin_sasl_mechanism: str = "SCRAM-SHA-256"
    replica: int = 1
    partition: int = 4
    tenant_password: None | str = None
    tenant_sasl_mechanism: str = "SCRAM-SHA-256"
    admin_api_base_url: str = "http://localhost:9644"


def kafka_client(properties: RedpandaProperties) -> AdminClient:
    """
    Create a Kafka AdminClient
    """
    # Kafka client configuration
    conf = {
        "bootstrap.servers": properties.broker,
        "security.protocol": properties.security_protocol,
        "sasl.mechanism": properties.admin_sasl_mechanism,
        "sasl.username": properties.admin_username,
        "sasl.password": properties.admin_password,
        "receive.message.max.bytes": 1213486160,
    }
    return AdminClient(conf)


def create_topics(properties: RedpandaProperties) -> bool:
    """
    Create topics for the given tenant and environment
    """
    try:
        client = kafka_client(properties)
        topics = [
            NewTopic(
                f"zsegment-{properties.tenant}-{properties.environment}-inbound",
                num_partitions=properties.partition,
                replication_factor=properties.replica,
            ),
            NewTopic(
                f"zsegment-{properties.tenant}-{properties.environment}-outbound",
                num_partitions=properties.partition,
                replication_factor=properties.replica,
            ),
            NewTopic(
                f"zsegment-{properties.tenant}-{properties.environment}-event",
                num_partitions=properties.partition,
                replication_factor=properties.replica,
            ),
        ]

        response = client.create_topics(topics)

        # Check if each topic was successfully created or had an exception
        success = True
        for topic, future in response.items():
            try:
                # This will raise an exception if topic creation failed
                future.result()
                log_info(f"Topic '{topic}' created successfully.")
            except KafkaError as e:
                success = False
                log_error(f"Failed to create topic '{topic}': {e}")

        if success:
            log_info(f"All topics created successfully for tenant '{properties.tenant}'.")
        else:
            log_error(f"Some topics failed to create for tenant '{properties.tenant}'.")

        return success

    except KafkaError as e:
        log_error(f"Error creating topics: {e}")
        return False


def delete_topics(properties: RedpandaProperties) -> bool:
    """
    Delete topics for the given tenant and environment
    """
    try:
        client = kafka_client(properties)
        topics = [
            f"zsegment-{properties.tenant}-{properties.environment}-inbound",
            f"zsegment-{properties.tenant}-{properties.environment}-outbound",
            f"zsegment-{properties.tenant}-{properties.environment}-event",
        ]
        client.delete_topics(topics)
        log_info(f"Deleted topics for tenant {properties.tenant}")
        return True
    except KafkaError as e:
        log_error(f"Failed to delete topics: {e}")
        return False


def create_acls(properties: RedpandaProperties) -> bool:
    """
    Create ACLs for the given tenant and broker.
    """
    try:
        # Create Kafka AdminClient
        admin = kafka_client(properties)

        # Define access control entries (ACE) for both topic and group resources
        access_control_entries = [
            # ACL for topics with tenant prefix
            AclBinding(
                restype=ResourceType.TOPIC,
                name=f"zsegment-{properties.tenant}-",
                resource_pattern_type=ResourcePatternType.PREFIXED,
                principal=f"User:zsegment_{properties.tenant}",
                host="*",
                operation=AclOperation.ALL,
                permission_type=AclPermissionType.ALLOW,
            ),
            # ACL for consumer groups with tenant prefix
            AclBinding(
                restype=ResourceType.GROUP,
                name=f"zsegment-{properties.tenant}-",
                resource_pattern_type=ResourcePatternType.PREFIXED,
                principal=f"User:zsegment_{properties.tenant}",
                host="*",
                operation=AclOperation.ALL,
                permission_type=AclPermissionType.ALLOW,
            ),
        ]

        # Create the ACLs
        futures = admin.create_acls(access_control_entries).values()
        # Wait for all futures to complete
        done, not_done = wait(futures, return_when=ALL_COMPLETED)

        # Check if any task encountered an exception
        for future in done:
            if future.exception() is not None:
                log_error(f"Failed to create ACL: {future.exception()}")
                return False

        log_info(f"All ACLs successfully created for tenant {properties.tenant}")
        return True
    except Exception as e:
        log_error(f"Failed to create ACLs: {e}")
        return False


def create_user(properties: RedpandaProperties) -> bool:
    """
    Create a user for the given tenant
    """
    try:
        client = httpx.Client()
        user_payload = {
            "username": f"zsegment_{properties.tenant}",
            "algorithm": properties.tenant_sasl_mechanism,
            "password": properties.tenant_password,
        }
        response = client.post(f"{properties.admin_api_base_url}/v1/security/users", json=user_payload)
        if response.status_code == 200:
            log_info(f"Created user for tenant {properties.tenant}")
            return True
        else:
            log_error(f"Failed to create user: {response.status_code}")
            return False
    except httpx.HTTPStatusError as e:
        log_error(f"Failed to create user: {e}")
        return False


def delete_user(properties: RedpandaProperties) -> bool:
    """
    Delete a user for the given tenant
    """
    try:
        client = httpx.Client()
        response = client.delete(f"{properties.admin_api_base_url}/v1/security/users/{properties.tenant}")
        if response.status_code == 200:
            log_info(f"Deleted user for tenant {properties.tenant}")
            return True
        else:
            log_error(f"Failed to delete user: {response.status_code}")
            return False
    except httpx.HTTPStatusError as e:
        log_error(f"Failed to delete user: {e}")
        return False


class RedpandaSetupActivity(Activity):
    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="RedpandaSetupActivity")
    async def defn(properties: RedpandaProperties) -> None:
        """
        Complete Redpanda setup by creating a user, ACLs, and topics for the tenant.
        """
        log_info(f"Starting Redpanda setup for tenant {properties.__dict__}")

        # Step 1: Create user
        user_created = create_user(properties)
        if not user_created:
            log_error(f"Failed to create user for tenant {properties.tenant}")
        log_info(f"User created successfully for tenant {properties.tenant}")

        # Step 2: Set up ACLs
        acls_created = create_acls(properties)
        if not acls_created:
            log_error(f"Failed to create ACLs for tenant {properties.tenant}")
        log_info(f"ACLs created successfully for tenant {properties.tenant}")

        # Step 3: Create topics for each environment stage if provided
        if properties.environment:
            topics_created = create_topics(properties)
            if not topics_created:
                log_error(
                    f"Failed to create topics for tenant {properties.tenant} in environment {properties.environment}"
                )
            log_info(
                f"Topics created successfully for tenant {properties.tenant} in environment {properties.environment}"
            )

        log_info(f"Redpanda setup completed for tenant {properties.tenant}")
