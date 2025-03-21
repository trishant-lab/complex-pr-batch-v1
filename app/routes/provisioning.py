import datetime
import re
import uuid
from typing import TYPE_CHECKING

import aiohttp
from fastapi import APIRouter, BackgroundTasks, Depends, Path
from loguru import logger
from pydantic import BaseModel
from starlette.requests import Request
from temporalio import client
from temporalio.api.common.v1 import WorkflowExecution
from temporalio.api.enums.v1 import EventType
from temporalio.api.workflowservice.v1 import (
    GetWorkflowExecutionHistoryRequest,
    GetWorkflowExecutionHistoryResponse,
    ListArchivedWorkflowExecutionsRequest,
    ListWorkflowExecutionsRequest,
)
from temporalio.client import WorkflowHandle

from app.core.db import DBManager, get_db_manager
from app.core.ijson import ijson_dumps, ijson_loads
from app.core.oauth2 import get_oauth_scheme
from app.core.settings import AppSettings, get_settings
from app.exceptions import errors
from app.models.form_schema.product_schema import ProductFormSchema
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum
from app.routes.product import get_product
from app.routes.tenant import TenantCreateRequestModel, create_tenant, get_existing_tenant_names
from app.slack_utils import send_slack_msg

provisioning_router = APIRouter()


if TYPE_CHECKING:
    from app.cli.base_workflow import ProductWorkflow


async def send_slack_notification(product: ProductEnum, schema: dict, approval_required: bool, tenant_id: str) -> None:
    """
    Send Slack notification
    """
    config: AppSettings = get_settings()
    schema_details = "\n".join(
        [
            f"{key}: {value}"
            for key, value in schema.items()
            if value and key in ["firstName", "lastName", "organization", "email"]
        ]
    )
    text = f"A new {product.value} tenant has been requested by \n {schema_details}"
    blocks = [
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text,
            },
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*TenantName:* {schema['tenant']}",
                }
            ],
        },
    ]
    if approval_required:
        extended_block = [
            {
                "type": "section",
                "fields": [{"type": "mrkdwn", "text": "*Approval Required:*"}],
            },
            {
                "type": "rich_text",
                "elements": [
                    {
                        "type": "rich_text_section",
                        "elements": [
                            {
                                "type": "link",
                                "url": f"{config.app_url}/tenant-details?id={tenant_id}",
                            }
                        ],
                    }
                ],
            },
        ]
        blocks.extend(extended_block)

    blocks.append({"type": "divider"})

    send_slack_msg(product=product, text=text, blocks=blocks)


@provisioning_router.get(
    "/validateEmail",
    operation_id="validateEmail",
)
def validate_email(email: str) -> None:
    """
    Validate email address
    """
    # List of public domains to exclude
    public_domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com"]

    # Regular expression for basic email validation
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

    if not re.match(email_regex, email):
        raise errors.INVALID_EMAIL.exc()

    # Extract the domain part of the email
    domain = email.split("@")[1]

    # Check if the domain is in the list of public domains
    if domain in public_domains:
        raise errors.INVALID_EMAIL.exc()


@provisioning_router.post(
    "",
    operation_id="provisioning",
)
async def provisioning(
    provisioning_details: ProductFormSchema,
    request: Request,
    skip_approval: bool = False,
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> None:
    """
    Trigger provisioning workflow for the given product
    """
    product = provisioning_details.product
    schema = provisioning_details.form_data
    user_id: str = request.scope.get("user", {}).get("sub")
    product_details = await get_product(product=product)
    if not product_details:
        raise errors.PRODUCT_NOT_FOUND.exc()
    product_details = dict(product_details)

    existing_tenant_names = await get_existing_tenant_names(
        product=product, email=None, tenant_names=[schema.tenant.lower()]
    )

    if existing_tenant_names:
        raise errors.ALREADY_ALLOCATED_TENANT_NAME.exc()

    schema_data = schema.model_dump()
    # Create tenant
    tenant_details = await create_tenant(
        TenantCreateRequestModel(
            tenantname=schema.tenant.lower(),
            email=schema.email,
            orgname=schema.organization,
            product=product,
            product_schema=ijson_dumps(product_details["product_schema"]),
            status=(
                TenantStatusEnum.Provisioning
                if product_details["approvalRequired"] and skip_approval
                else TenantStatusEnum.PendingApproval
            ),
            approvedBy=user_id if skip_approval else None,
            schema_=ijson_dumps(schema_data),
        ),
    )

    product_workflow: ProductWorkflow = ProductEnum.get_class(product)()
    schema_data["customerId"] = tenant_details.get("id")
    await product_workflow.onboard(schema_data)
    logger.info(f"Triggered provisioning workflow for product: {product.value}")

    background_tasks.add_task(
        send_slack_notification,
        product=product,
        schema=schema_data,
        approval_required=True if product_details["approvalRequired"] and not skip_approval else False,
        tenant_id=tenant_details.get("id"),
    )

    if product_details["approvalRequired"] and skip_approval:
        logger.info(f"Skipping approval for product: {product.value}")
        await product_workflow.approve(schema_data)


@provisioning_router.post("/approveOrDecline/{product}", operation_id="approveOrDecline")
async def approve_tenant(
    approval: bool,
    tenant_id: uuid.UUID,
    request: Request,
    tenant_name: None | str = None,
    product: ProductEnum = Path(...),
    _: dict = Depends(get_oauth_scheme()),
) -> None:
    """
    Approve tenant
    """
    user_id: dict = request.scope.get("user", {}).get("sub")

    db: DBManager = await get_db_manager()
    response = await db.fetch_one("get_tenant.sql", tenant_id=str(tenant_id))  # NOSONAR
    tenant_params = {"table": "customer", "payload": {"approvedBy": user_id}, "where": f"id={tenant_id!s}"}
    operator_params = {
        "table": "operatorstatus",
        "payload": {"status": TenantStatusEnum.Provisioning if approval else TenantStatusEnum.Declined},
        "where": f"cutomerid={tenant_id!s}",
    }
    await db.execute_many([("put.sql", tenant_params), ("put.sql", operator_params)])

    schema = ijson_loads(response["schema"])

    product_workflow: ProductWorkflow = ProductEnum.get_class(product)()

    if approval:
        if tenant_name and schema["tenant"] != tenant_name:
            workflow_handle: WorkflowHandle = await product_workflow.get_workflow_handle(schema=schema)

            response = await workflow_handle.describe()

            if response.status.name == "RUNNING":
                # terminate the workflow
                await workflow_handle.terminate()

            # start the workflow
            schema["tenant"] = tenant_name
            await db.fetch_one(
                "update_tenant_name.sql",
                tenant_id=str(tenant_id),
                tenant_name=tenant_name,
                product_schema=ijson_dumps(schema),
            )

            schema["emailSent"] = True
            await product_workflow.onboard(schema)
            await product_workflow.approve(schema)

        else:
            await product_workflow.approve(schema)
            logger.info(f"Approved {response['product']} workflow for tenant: {response['tenantname']}")

    else:
        await product_workflow.decline(schema)
        logger.info(f"Declined {response['product']} workflow for tenant: {response['tenantname']}")


@provisioning_router.post("/retryProvisioning/{product}", operation_id="retryProvisioning")
async def retry_provisioning(
    tenant_id: uuid.UUID,
    product: ProductEnum = Path(...),
    _: dict = Depends(get_oauth_scheme()),
) -> None:
    """
    Retry provisioning
    """
    product_details = await get_product(product=product)
    if not product_details:
        raise errors.PRODUCT_NOT_FOUND.exc()

    try:
        db: DBManager = await get_db_manager()
        response = await db.fetch_one("get_tenant.sql", tenant_id=str(tenant_id))
        await db.fetch_one(
            "update_tenant.sql",
            tenant_name=response["name"],
            status=TenantStatusEnum.Provisioning.value,
            product=product.value,
        )
        schema = ijson_loads(response["schema"])
        schema["emailSent"] = True

        product_details = dict(product_details)

        product_workflow: ProductWorkflow = ProductEnum.get_class(product)()
        await product_workflow.onboard(schema)

        if product_details["approvalRequired"]:
            await product_workflow.approve(schema)

        # await product_workflow.approve(schema)
        logger.info(f"Retried provisioning workflow for tenant: {response['tenantname']}")
    except Exception as e:
        logger.error(f"Error retrying provisioning: {e}")
        raise errors.RETRY_PROVISIONING_ERROR.exc(e=e)


class Logs(BaseModel):
    loglevel: str
    log: str


class WorkflowSteps(BaseModel):
    activityName: str
    status: str
    logs: list[Logs]


async def get_grafana_logs(config: AppSettings, workflow_id: str, from_: datetime.datetime) -> dict:
    """
    Get Grafana logs
    """
    url = f"{config.grafana_url}/api/ds/query"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {config.grafana_token}"}
    expr = f'{{k8s_app="launchpad-cli"}} |= `workflow_id={workflow_id}` | json'

    from_ = int(from_.timestamp()) * 1000
    to_ = int(datetime.datetime.now().timestamp()) * 1000

    payload = ijson_dumps(
        {
            "queries": [
                {
                    "expr": expr,
                    "queryType": "range",
                    "refId": "loki-data-samples",
                    "maxLines": 5000,
                    "supportingQueryType": "dataSample",
                    "legendFormat": "",
                    "datasource": {"type": "loki", "uid": config.grafana_datasource_uid},
                    "datasourceId": 2,
                    "intervalMs": 10800000,
                }
            ],
            "from": str(from_),
            "to": str(to_),
        }
    )

    async with aiohttp.ClientSession() as session:
        response = await session.post(url, headers=headers, data=payload, timeout=aiohttp.ClientTimeout(total=120))

        response.raise_for_status()

        response_json = await response.json()
    logs = {}
    for log in response_json["results"]["loki-data-samples"]["frames"][0]["data"]["values"][0]:
        loglevel_match = re.search(r"loglevel=(\w+)", log["message"])
        activity_log = re.search(r"activity_name:[^ ]+ (.+)", log["message"])
        activity_name = re.search(r"activity_name:([^ ]+)", log["message"])

        loglevel = loglevel_match.group(1) if loglevel_match else None
        activity_name_ = activity_name.group(1) if activity_name else None
        activity_log_ = activity_log.group(1).strip().replace('"', "") if activity_log else None

        if activity_name_ in logs:
            if activity_log_ not in [log["log"] for log in logs[activity_name_]]:
                logs[activity_name_].append({"loglevel": loglevel, "log": activity_log_})
        else:
            logs[activity_name_] = [{"loglevel": loglevel, "log": activity_log_}]
    return logs


async def fetch_workflow_history(workflow_id: str, run_id: str) -> GetWorkflowExecutionHistoryResponse:
    """
    Fetch archived workflow history
    """
    # Connect to Temporal gRPC service
    config: AppSettings = get_settings()
    temporal_client = await client.Client.connect(config.temporal.dsn)

    # Request archived workflow history
    # history_event_filter_type: 0 = ALL_EVENTS, 1 = CLOSE_EVENT_ONLY
    request = GetWorkflowExecutionHistoryRequest(
        namespace=config.temporal.namespace,
        execution=WorkflowExecution(workflow_id=workflow_id, run_id=run_id),
        history_event_filter_type=0,
    )

    return await temporal_client.workflow_service.get_workflow_execution_history(request)


async def get_latest_run_id_by_workflow_id(workflow_id: str) -> str | None:
    """
    Get latest run id by workflow id
    """
    config: AppSettings = get_settings()
    temporal_client = await client.Client.connect(config.temporal.dsn)

    # 1️⃣ Check in current (non-archived) workflows
    request = ListWorkflowExecutionsRequest(
        namespace=config.temporal.namespace,
        query=f'WorkflowId = "{workflow_id}"',
    )
    response = await temporal_client.workflow_service.list_workflow_executions(request)

    if response.executions:
        max_close_time = max(execution.close_time.ToDatetime() for execution in response.executions)
        execution = [  # noqa: RUF015
            execution for execution in response.executions if execution.close_time.ToDatetime() == max_close_time
        ][0]
        logger.info(
            f"Found in active workflows: {execution.execution.workflow_id}, Run ID: {execution.execution.run_id}"
        )
        return execution.execution.run_id

    # 2️⃣ If not found, check archived workflows
    logger.info("Not found in active workflows, checking archives...")
    archive_request = ListArchivedWorkflowExecutionsRequest(
        namespace=config.temporal.namespace,
        query=f'WorkflowId = "{workflow_id}"',
    )
    archive_response = await temporal_client.workflow_service.list_archived_workflow_executions(archive_request)

    if archive_response.executions:
        max_close_time = max(execution.close_time.ToDatetime() for execution in archive_response.executions)
        execution = [  # noqa: RUF015
            execution
            for execution in archive_response.executions
            if execution.close_time.ToDatetime() == max_close_time
        ][0]
        logger.info(f"Found in archives: {execution.execution.workflow_id}, Run ID: {execution.execution.run_id}")
        return execution.execution.run_id

    logger.info("No workflow found in active or archived executions.")
    return None


@provisioning_router.get("/workflowSteps/{product}", operation_id="workflowSteps")
async def get_workflow_steps(
    tenant_id: uuid.UUID,
    product: ProductEnum = Path(...),
    _: dict = Depends(get_oauth_scheme()),
) -> list[WorkflowSteps]:
    """
    Get workflow steps and logs
    """
    config: AppSettings = get_settings()
    try:
        db: DBManager = await get_db_manager()
        response = await db.fetch_one("get_tenant.sql", tenant_id=str(tenant_id))
        schema = ijson_loads(response["schema"])
    except Exception as e:
        logger.error(f"Error fetching tenant: {e}")
        raise errors.TENANT_NOT_FOUND.exc()

    try:
        product_workflow: ProductWorkflow = ProductEnum.get_class(product)()

        workflow_id: str = product_workflow.get_workflow_id(schema)
        run_id: str = await get_latest_run_id_by_workflow_id(workflow_id)

        workflow_response: GetWorkflowExecutionHistoryResponse = await fetch_workflow_history(workflow_id, run_id)
    except Exception as e:
        logger.error(f"Error fetching workflow history: {e}")
        raise errors.WORKFLOW_HISTORY_FETCH_ERROR.exc(e=e)

    workflow_steps = {}
    for event in workflow_response.history.events:
        event_type = EventType.Name(event.event_type)
        if event_type == "EVENT_TYPE_ACTIVITY_TASK_SCHEDULED":
            workflow_steps[event.event_id] = {
                "activityName": event.activity_task_scheduled_event_attributes.activity_type.name,
                "status": "scheduled",
            }

        if event_type == "EVENT_TYPE_ACTIVITY_TASK_STARTED":
            workflow_steps.get(event.activity_task_started_event_attributes.scheduled_event_id).update(
                {"status": "started"}
            )
        if event_type == "EVENT_TYPE_ACTIVITY_TASK_COMPLETED":
            workflow_steps.get(event.activity_task_completed_event_attributes.scheduled_event_id).update(
                {"status": "completed"}
            )

        if event_type == "EVENT_TYPE_ACTIVITY_TASK_FAILED":
            workflow_steps.get(event.activity_task_failed_event_attributes.scheduled_event_id).update(
                {
                    "status": "failed",
                    "logs": [{"log": event.activity_task_failed_event_attributes.failure.message, "loglevel": "ERROR"}],
                }
            )

    logs = await get_grafana_logs(config, workflow_id=workflow_id, from_=response.get("created"))

    [
        activity.update({"logs": logs.get(activity["activityName"], activity.get("logs", []))})
        for activity in workflow_steps.values()
    ]

    return [WorkflowSteps(**activity) for activity in workflow_steps.values()]
