from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

from app.temporalworkflows.common.keyclaokrealmsetup.keyclaokrealmcreationactivity import \
    create_keycloak_realm_activity, CreateKeycloakRealmActivityInput


@dataclass
class KeyclaokRealmCreationWorkflowInput:
    product: str
    tenant: str
    tenant_url: str
    realm_name: str
    domain_org: str
    customer_username: str
    customer_email: str
    admin_user: str
    admin_email: str
    customer_realm_roles: list[str]


@workflow.defn(name="keyclaokrealmcreation_workflow", sandboxed=False)
class KeyclaokRealmCreationWorkflow:
    @workflow.run
    async def run(self, workflow_input: KeyclaokRealmCreationWorkflowInput) -> None:
        """
        :return:
        """

        # Create keycloak realm, Create tenant admin user and customer admin user
        await workflow.execute_activity(
            create_keycloak_realm_activity,
            CreateKeycloakRealmActivityInput(
                realm_name=workflow_input.realm_name,
                product=workflow_input.product,
                customerRealmRoles=workflow_input.customer_realm_roles,
                tenant=workflow_input.tenant,
                tenant_url=workflow_input.tenant_url,
                customer_username=workflow_input.customer_username,
                customer_email=workflow_input.customer_email,
                admin_user=workflow_input.admin_user,
                admin_email=workflow_input.admin_email,
            ),
            retry_policy=RetryPolicy(
                backoff_coefficient=2.0,
                maximum_attempts=1,
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=60),
            ),
            start_to_close_timeout=timedelta(seconds=120)
        )
